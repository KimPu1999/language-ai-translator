from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import error_payload
from app.core.rate_limit import InMemorySpeechRateLimiter, get_speech_rate_limiter
from app.core.text import character_count
from app.db.session import get_db
from app.providers.speech.base import SpeechProviderError
from app.providers.speech.mapping import BY_LOCALE
from app.providers.speech.registry import SpeechProviderRegistry, get_speech_registry
from app.repositories.speech_usage import record_speech_usage_event
from app.schemas.voice import VoiceSynthesisRequest, VoiceTranscriptionResponse
from app.services.audio import (
    ALLOWED_AUDIO_CONTENT_TYPES,
    MAX_AUDIO_BYTES,
    AudioInputError,
    convert_to_pcm_wav,
)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


def _error(
    code: str,
    message: str,
    request: Request,
    status_code: int,
    retry_after: str | None = None,
):
    headers = {"Retry-After": retry_after} if retry_after else None
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, request_id=request.state.request_id),
        headers=headers,
    )


async def _record(
    db: AsyncSession,
    request: Request,
    *,
    operation: str,
    provider: str,
    locale: str,
    voice: str | None,
    input_bytes: int,
    duration_ms: int | None,
    characters: int,
    started: float,
    status: str,
    error_code: str | None = None,
) -> None:
    await record_speech_usage_event(
        db,
        request_id=request.state.request_id,
        operation=operation,
        provider=provider,
        locale=locale,
        voice=voice,
        input_bytes=input_bytes,
        duration_ms=duration_ms,
        character_count=characters,
        status=status,
        latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
        error_code=error_code,
    )


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe(
    request: Request,
    locale: str = Query(..., min_length=2, max_length=16),
    registry: SpeechProviderRegistry = Depends(get_speech_registry),
    limiter: InMemorySpeechRateLimiter = Depends(get_speech_rate_limiter),
    db: AsyncSession = Depends(get_db),
) -> Any:
    started = time.perf_counter()
    provider = registry.recognition
    provider_name = provider.name if provider else "none"
    if provider is None:
        return _error(
            "SPEECH_ENGINE_NOT_CONFIGURED",
            "Speech recognition is not configured",
            request,
            503,
        )
    capability = BY_LOCALE.get(locale)
    if capability is None or not capability.stt_enabled:
        return _error("UNSUPPORTED_SPEECH_LANGUAGE", "Unsupported speech locale", request, 422)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type not in ALLOWED_AUDIO_CONTENT_TYPES:
        return _error("UNSUPPORTED_AUDIO_FORMAT", "Unsupported audio format", request, 422)

    chunks: list[bytes] = []
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > MAX_AUDIO_BYTES:
            return _error("AUDIO_TOO_LARGE", "Audio must be 5 MB or smaller", request, 413)
        chunks.append(chunk)
    audio_data = b"".join(chunks)
    input_bytes = len(audio_data)
    if input_bytes == 0:
        return _error("INVALID_AUDIO", "Audio input is required", request, 422)

    decision = await limiter.check(_client_key(request), input_bytes=input_bytes)
    if not decision.allowed:
        return _error(
            decision.code or "SPEECH_RATE_LIMIT_EXCEEDED",
            "Speech usage limit reached",
            request,
            429,
            str(decision.retry_after),
        )

    duration_ms: int | None = None
    try:
        wav_data, duration_ms = await convert_to_pcm_wav(audio_data)
        result = await provider.recognize(audio_data=wav_data, locale=locale)
    except AudioInputError as error:
        await _record(
            db,
            request,
            operation="transcribe",
            provider=provider_name,
            locale=locale,
            voice=None,
            input_bytes=input_bytes,
            duration_ms=duration_ms,
            characters=0,
            started=started,
            status="error",
            error_code=error.code,
        )
        return _error(error.code, error.message, request, error.status_code)
    except SpeechProviderError as error:
        await _record(
            db,
            request,
            operation="transcribe",
            provider=provider_name,
            locale=locale,
            voice=None,
            input_bytes=input_bytes,
            duration_ms=duration_ms,
            characters=0,
            started=started,
            status="error",
            error_code=error.code,
        )
        return _error(error.code, error.message, request, error.status_code, error.retry_after)

    await _record(
        db,
        request,
        operation="transcribe",
        provider=result.provider,
        locale=result.locale,
        voice=None,
        input_bytes=input_bytes,
        duration_ms=duration_ms,
        characters=0,
        started=started,
        status="success",
    )
    return VoiceTranscriptionResponse(
        transcript=result.text,
        locale=result.locale,
        provider=result.provider,
        request_id=request.state.request_id,
    )


@router.post("/synthesize")
async def synthesize(
    request: Request,
    payload: VoiceSynthesisRequest,
    registry: SpeechProviderRegistry = Depends(get_speech_registry),
    limiter: InMemorySpeechRateLimiter = Depends(get_speech_rate_limiter),
    db: AsyncSession = Depends(get_db),
) -> Response:
    started = time.perf_counter()
    provider = registry.synthesis
    provider_name = provider.name if provider else "none"
    characters = character_count(payload.text)
    if provider is None:
        return _error(
            "SPEECH_ENGINE_NOT_CONFIGURED",
            "Speech synthesis is not configured",
            request,
            503,
        )
    capability = BY_LOCALE.get(payload.locale)
    if capability is None or not capability.tts_enabled:
        return _error("UNSUPPORTED_SPEECH_LANGUAGE", "Unsupported speech locale", request, 422)
    if payload.voice not in {voice.name for voice in capability.voices}:
        return _error("UNSUPPORTED_SPEECH_VOICE", "Unsupported speech voice", request, 422)

    decision = await limiter.check(_client_key(request), characters=characters)
    if not decision.allowed:
        return _error(
            decision.code or "SPEECH_RATE_LIMIT_EXCEEDED",
            "Speech usage limit reached",
            request,
            429,
            str(decision.retry_after),
        )

    try:
        result = await provider.synthesize(
            text=payload.text, locale=payload.locale, voice=payload.voice
        )
        if not result.audio_data.startswith(b"RIFF") or b"WAVE" not in result.audio_data[:16]:
            raise SpeechProviderError(
                "SPEECH_INVALID_AUDIO_RESPONSE",
                "Speech provider returned invalid audio",
                status_code=502,
            )
    except SpeechProviderError as error:
        await _record(
            db,
            request,
            operation="synthesize",
            provider=provider_name,
            locale=payload.locale,
            voice=payload.voice,
            input_bytes=0,
            duration_ms=None,
            characters=characters,
            started=started,
            status="error",
            error_code=error.code,
        )
        return _error(error.code, error.message, request, error.status_code, error.retry_after)

    await _record(
        db,
        request,
        operation="synthesize",
        provider=result.provider,
        locale=result.locale,
        voice=result.voice,
        input_bytes=0,
        duration_ms=None,
        characters=characters,
        started=started,
        status="success",
    )
    return Response(
        content=result.audio_data,
        media_type="audio/wav",
        headers={"Content-Disposition": "inline", "X-Request-ID": request.state.request_id},
    )
