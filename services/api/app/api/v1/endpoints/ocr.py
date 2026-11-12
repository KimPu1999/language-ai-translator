from __future__ import annotations

import time

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import error_payload
from app.core.rate_limit import InMemoryOCRRateLimiter, get_ocr_rate_limiter
from app.db.session import get_db
from app.providers.ocr.base import OCRProviderError
from app.providers.ocr.mapping import SUPPORTED_APPLICATION_LANGUAGES
from app.providers.ocr.registry import OCRProviderRegistry, get_ocr_registry
from app.repositories.ocr_usage import record_ocr_usage_event
from app.schemas.ocr import OCRBlockResponse, OCRCapabilitiesResponse, OCRExtractResponse
from app.services.ocr_image import ALLOWED_IMAGE_TYPES, ImageInputError, preprocess_image

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


def _error(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, request_id=request.state.request_id),
    )


@router.get("/capabilities", response_model=OCRCapabilitiesResponse)
async def capabilities(
    registry: OCRProviderRegistry = Depends(get_ocr_registry),
) -> OCRCapabilitiesResponse:
    return OCRCapabilitiesResponse(
        provider=registry.provider.name if registry.provider else None,
        provider_configured=registry.configured,
        languages=list(registry.languages),
        experimental_languages=list(registry.experimental_languages),
        consent_required=registry.consent_required,
    )


@router.post("/extract", response_model=OCRExtractResponse)
async def extract(
    request: Request,
    image: UploadFile = File(...),
    language: str = Query(..., min_length=2, max_length=16),
    cloud_consent: bool = Form(False),
    registry: OCRProviderRegistry = Depends(get_ocr_registry),
    limiter: InMemoryOCRRateLimiter = Depends(get_ocr_rate_limiter),
    db: AsyncSession = Depends(get_db),
) -> OCRExtractResponse | JSONResponse:
    started = time.perf_counter()
    provider_name = registry.provider.name if registry.provider else "none"

    async def record(
        *,
        status: str,
        file_size: int,
        width: int | None = None,
        height: int | None = None,
        error_code: str | None = None,
        billable_units: int = 0,
    ) -> None:
        await record_ocr_usage_event(
            db,
            request_id=request.state.request_id,
            provider=provider_name,
            language=language,
            width=width,
            height=height,
            file_size=file_size,
            execution_ms=max(0, int((time.perf_counter() - started) * 1000)),
            status=status,
            error_code=error_code,
            billable_units=billable_units,
        )

    if language not in SUPPORTED_APPLICATION_LANGUAGES:
        await image.close()
        await record(status="error", file_size=0, error_code="UNSUPPORTED_OCR_LANGUAGE")
        return _error(request, "UNSUPPORTED_OCR_LANGUAGE", "Unsupported OCR language", 422)
    if registry.provider is None:
        await image.close()
        await record(status="error", file_size=0, error_code="OCR_PROVIDER_NOT_CONFIGURED")
        return _error(request, "OCR_PROVIDER_NOT_CONFIGURED", "OCR is not configured", 503)
    if registry.consent_required and not cloud_consent:
        await image.close()
        await record(status="error", file_size=0, error_code="OCR_CLOUD_CONSENT_REQUIRED")
        return _error(
            request,
            "OCR_CLOUD_CONSENT_REQUIRED",
            "Explicit consent is required before this image is sent to cloud OCR",
            400,
        )
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        await image.close()
        await record(status="error", file_size=0, error_code="UNSUPPORTED_IMAGE_TYPE")
        return _error(
            request, "UNSUPPORTED_IMAGE_TYPE", "Only JPEG, PNG, and WebP images are supported", 422
        )
    settings = get_settings()
    data = bytearray()
    while True:
        chunk = await image.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > settings.ocr_max_upload_bytes:
            await image.close()
            await record(status="error", file_size=len(data), error_code="IMAGE_TOO_LARGE")
            return _error(request, "IMAGE_TOO_LARGE", "Image upload must be 8 MB or smaller", 413)
    decision = await limiter.check(
        request.client.host if request.client else "unknown", input_bytes=len(data)
    )
    if not decision.allowed:
        await image.close()
        await record(status="error", file_size=len(data), error_code=decision.code)
        return JSONResponse(
            status_code=429,
            content=error_payload(
                decision.code or "OCR_RATE_LIMIT_EXCEEDED",
                "OCR usage limit reached",
                request_id=request.state.request_id,
            ),
            headers={"Retry-After": str(decision.retry_after)},
        )
    width: int | None = None
    height: int | None = None
    try:
        prepared = preprocess_image(bytes(data), settings, image.content_type)
        width, height = prepared.size
        result = await registry.provider.extract(image=prepared, language=language)
    except ImageInputError as error:
        await record(
            status="error",
            file_size=len(data),
            width=width,
            height=height,
            error_code=error.code,
        )
        return _error(request, error.code, error.message, error.status_code)
    except OCRProviderError as error:
        await record(
            status="error",
            file_size=len(data),
            width=width,
            height=height,
            error_code=error.code,
        )
        return _error(request, error.code, error.message, error.status_code)
    finally:
        await image.close()
    await record(
        status="success",
        file_size=len(data),
        width=width,
        height=height,
        billable_units=1 if provider_name == "google-cloud-vision" else 0,
    )
    return OCRExtractResponse(
        text=result.text,
        language=result.language,
        provider=result.provider,
        blocks=[OCRBlockResponse(**block.__dict__) for block in result.blocks],
        request_id=request.state.request_id,
    )
