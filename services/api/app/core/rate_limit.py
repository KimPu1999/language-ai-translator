from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request

from app.core.config import Settings, get_settings
from app.core.errors import error_payload
from app.core.text import character_count


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    code: str | None = None
    retry_after: int = 1


class InMemoryTranslationRateLimiter:
    def __init__(self, settings: Settings):
        self._request_limit = settings.rate_limit_requests
        self._character_limit = settings.rate_limit_characters
        self._window_seconds = settings.rate_limit_window_seconds
        self._buckets: dict[str, tuple[float, int, int]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, text: str) -> RateLimitDecision:
        now = time.monotonic()
        chars = character_count(text)
        async with self._lock:
            start, requests, characters = self._buckets.get(key, (now, 0, 0))
            if now - start >= self._window_seconds:
                start, requests, characters = now, 0, 0
            retry_after = max(1, int(self._window_seconds - (now - start)))
            if requests >= self._request_limit:
                return RateLimitDecision(False, "RATE_LIMIT_EXCEEDED", retry_after)
            if characters + chars > self._character_limit:
                return RateLimitDecision(False, "CHARACTER_USAGE_LIMIT_EXCEEDED", retry_after)
            self._buckets[key] = (start, requests + 1, characters + chars)
            return RateLimitDecision(True)


class InMemorySpeechRateLimiter:
    def __init__(self, settings: Settings):
        self._request_limit = settings.speech_rate_limit_requests
        self._byte_limit = settings.speech_rate_limit_bytes
        self._character_limit = settings.speech_rate_limit_characters
        self._window_seconds = settings.rate_limit_window_seconds
        self._buckets: dict[str, tuple[float, int, int, int]] = {}
        self._lock = asyncio.Lock()

    async def check(
        self, key: str, *, input_bytes: int = 0, characters: int = 0
    ) -> RateLimitDecision:
        now = time.monotonic()
        async with self._lock:
            start, requests, used_bytes, used_characters = self._buckets.get(key, (now, 0, 0, 0))
            if now - start >= self._window_seconds:
                start, requests, used_bytes, used_characters = now, 0, 0, 0
            retry_after = max(1, int(self._window_seconds - (now - start)))
            if requests >= self._request_limit:
                return RateLimitDecision(False, "SPEECH_RATE_LIMIT_EXCEEDED", retry_after)
            if used_bytes + input_bytes > self._byte_limit:
                return RateLimitDecision(False, "SPEECH_BYTE_USAGE_LIMIT_EXCEEDED", retry_after)
            if used_characters + characters > self._character_limit:
                return RateLimitDecision(
                    False, "SPEECH_CHARACTER_USAGE_LIMIT_EXCEEDED", retry_after
                )
            self._buckets[key] = (
                start,
                requests + 1,
                used_bytes + input_bytes,
                used_characters + characters,
            )
            return RateLimitDecision(True)


class InMemoryOCRRateLimiter:
    def __init__(self, settings: Settings):
        self._request_limit = settings.ocr_rate_limit_requests
        self._byte_limit = settings.ocr_rate_limit_bytes
        self._window_seconds = settings.rate_limit_window_seconds
        self._buckets: dict[str, tuple[float, int, int]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, *, input_bytes: int) -> RateLimitDecision:
        now = time.monotonic()
        async with self._lock:
            start, requests, used_bytes = self._buckets.get(key, (now, 0, 0))
            if now - start >= self._window_seconds:
                start, requests, used_bytes = now, 0, 0
            retry_after = max(1, int(self._window_seconds - (now - start)))
            if requests >= self._request_limit:
                return RateLimitDecision(False, "OCR_RATE_LIMIT_EXCEEDED", retry_after)
            if used_bytes + input_bytes > self._byte_limit:
                return RateLimitDecision(False, "OCR_BYTE_USAGE_LIMIT_EXCEEDED", retry_after)
            self._buckets[key] = (start, requests + 1, used_bytes + input_bytes)
            return RateLimitDecision(True)


_limiter = InMemoryTranslationRateLimiter(get_settings())
_speech_limiter = InMemorySpeechRateLimiter(get_settings())
_ocr_limiter = InMemoryOCRRateLimiter(get_settings())


def get_translation_rate_limiter() -> InMemoryTranslationRateLimiter:
    return _limiter


def get_speech_rate_limiter() -> InMemorySpeechRateLimiter:
    return _speech_limiter


def get_ocr_rate_limiter() -> InMemoryOCRRateLimiter:
    return _ocr_limiter


async def enforce_translation_rate_limit(
    request: Request,
    text: str,
    limiter: InMemoryTranslationRateLimiter,
) -> None:
    decision = await limiter.check(request.client.host if request.client else "unknown", text)
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=error_payload(
                decision.code or "RATE_LIMIT_EXCEEDED", "Translation usage limit reached"
            ),
            headers={"Retry-After": str(decision.retry_after)},
        )
