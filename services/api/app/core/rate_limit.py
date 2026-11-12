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


_limiter = InMemoryTranslationRateLimiter(get_settings())


def get_translation_rate_limiter() -> InMemoryTranslationRateLimiter:
    return _limiter


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
