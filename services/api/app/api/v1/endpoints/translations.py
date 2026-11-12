import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import error_payload
from app.core.rate_limit import (
    InMemoryTranslationRateLimiter,
    enforce_translation_rate_limit,
    get_translation_rate_limiter,
)
from app.core.text import character_count
from app.db.session import get_db
from app.providers.translation.base import TranslationProviderError
from app.providers.translation.registry import TranslationProviderRegistry, get_translation_registry
from app.repositories.usage import record_usage_event
from app.schemas.translation import (
    LanguageDetectionRequest,
    LanguageDetectionResponse,
    TextTranslationRequest,
    TextTranslationResponse,
)
from app.services.detection import LanguageDetectionService
from app.services.translation import TranslationService

router = APIRouter(prefix="/api/v1/translations", tags=["translations"])


def _provider_error(error: TranslationProviderError, request: Request) -> JSONResponse:
    headers = {"Retry-After": error.retry_after} if error.retry_after else None
    return JSONResponse(
        status_code=error.status_code,
        content=error_payload(error.code, error.message, request_id=request.state.request_id),
        headers=headers,
    )


async def _record(
    db: AsyncSession,
    request: Request,
    *,
    operation: str,
    provider: str,
    source_language: str | None,
    target_language: str | None,
    text: str,
    started: float,
    status: str,
    error_code: str | None = None,
) -> None:
    await record_usage_event(
        db,
        request_id=request.state.request_id,
        operation=operation,
        provider=provider,
        source_language=source_language,
        target_language=target_language,
        character_count=character_count(text),
        status=status,
        latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
        error_code=error_code,
    )


def _provider_name(registry: TranslationProviderRegistry, operation: str) -> str:
    provider = registry.get_for(operation)
    return provider.name if provider else "none"


@router.post("/text", response_model=TextTranslationResponse)
async def translate_text(
    request: Request,
    payload: TextTranslationRequest,
    registry: TranslationProviderRegistry = Depends(get_translation_registry),
    limiter: InMemoryTranslationRateLimiter = Depends(get_translation_rate_limiter),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await enforce_translation_rate_limit(request, payload.text, limiter)
    started = time.perf_counter()
    try:
        result = await TranslationService(registry).translate(
            source_language=payload.source_language,
            target_language=payload.target_language,
            text=payload.text,
        )
    except TranslationProviderError as error:
        await _record(
            db,
            request,
            operation="translate",
            provider=_provider_name(registry, "text_translation"),
            source_language=payload.source_language,
            target_language=payload.target_language,
            text=payload.text,
            started=started,
            status="error",
            error_code=error.code,
        )
        return _provider_error(error, request)
    await _record(
        db,
        request,
        operation="translate",
        provider=result.provider,
        source_language=payload.source_language,
        target_language=payload.target_language,
        text=payload.text,
        started=started,
        status="success",
    )
    return TextTranslationResponse(
        translated_text=result.translated_text,
        provider=result.provider,
        detected_language=result.detected_language,
        request_id=request.state.request_id,
    )


@router.post("/detect", response_model=LanguageDetectionResponse)
async def detect_language(
    request: Request,
    payload: LanguageDetectionRequest,
    registry: TranslationProviderRegistry = Depends(get_translation_registry),
    limiter: InMemoryTranslationRateLimiter = Depends(get_translation_rate_limiter),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await enforce_translation_rate_limit(request, payload.text, limiter)
    started = time.perf_counter()
    try:
        result = await LanguageDetectionService(registry).detect(text=payload.text)
    except TranslationProviderError as error:
        await _record(
            db,
            request,
            operation="detect",
            provider=_provider_name(registry, "language_detection"),
            source_language=None,
            target_language=None,
            text=payload.text,
            started=started,
            status="error",
            error_code=error.code,
        )
        return _provider_error(error, request)
    await _record(
        db,
        request,
        operation="detect",
        provider=_provider_name(registry, "language_detection"),
        source_language=None,
        target_language=None,
        text=payload.text,
        started=started,
        status="success",
    )
    return LanguageDetectionResponse(
        language=result.language,
        score=result.score,
        alternatives=result.alternatives,
        request_id=request.state.request_id,
    )
