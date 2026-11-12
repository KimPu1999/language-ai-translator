from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import error_payload
from app.providers.documents.base import DocumentExtractionError
from app.providers.ocr.registry import OCRProviderRegistry, get_ocr_registry
from app.schemas.documents import (
    DocumentBlockResponse,
    DocumentCapabilitiesResponse,
    DocumentExtractResponse,
)
from app.services.documents import (
    SUPPORTED_FORMATS,
    DocumentExtractionService,
    segment_document_text,
)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _error(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, request_id=request.state.request_id),
    )


@router.get("/capabilities", response_model=DocumentCapabilitiesResponse)
async def capabilities(
    registry: OCRProviderRegistry = Depends(get_ocr_registry),
) -> DocumentCapabilitiesResponse:
    settings = get_settings()
    return DocumentCapabilitiesResponse(
        formats=list(SUPPORTED_FORMATS),
        max_upload_bytes=settings.document_max_upload_bytes,
        max_pages=settings.document_max_pages,
        max_characters=settings.document_max_characters,
        max_segment_characters=settings.document_max_segment_characters,
        ocr_fallback=registry.provider is not None,
    )


@router.post("/extract", response_model=DocumentExtractResponse)
async def extract(
    request: Request,
    document: UploadFile = File(...),
    source_language: str | None = Query(default=None, min_length=2, max_length=32),
    review_only: bool = Form(True),
    registry: OCRProviderRegistry = Depends(get_ocr_registry),
) -> DocumentExtractResponse | JSONResponse:
    del review_only  # Translation is intentionally not called by this endpoint.
    data = bytearray()
    try:
        while True:
            chunk = await document.read(1024 * 1024)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > get_settings().document_max_upload_bytes:
                return _error(
                    request, "DOCUMENT_TOO_LARGE", "Documents must be 10 MB or smaller", 413
                )
        service = DocumentExtractionService(ocr_registry=registry, settings=get_settings())
        result = await asyncio.to_thread(
            service.extract,
            bytes(data),
            filename=document.filename or "document",
            content_type=document.content_type,
            source_language=source_language,
        )
        return DocumentExtractResponse(
            format=result.format,
            text=result.text,
            blocks=[DocumentBlockResponse(**block.__dict__) for block in result.blocks],
            pages=result.pages,
            ocr_pages=list(result.ocr_pages),
            segments=list(
                segment_document_text(
                    result.text, limit=get_settings().document_max_segment_characters
                )
            ),
            request_id=request.state.request_id,
        )
    except DocumentExtractionError as error:
        return _error(request, error.code, error.message, error.status_code)
    finally:
        await document.close()
