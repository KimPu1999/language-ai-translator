from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class AuthRateDecision:
    allowed: bool
    retry_after: int = 1


class InMemoryAuthRateLimiter:
    """Bounded process-local fallback for development and single-instance use."""

    def __init__(self, settings: Settings, *, attempts: int | None = None) -> None:
        self._attempts = attempts or settings.auth_login_rate_limit_attempts
        self._window = settings.auth_rate_limit_window_seconds
        self._buckets: dict[str, tuple[float, int]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> AuthRateDecision:
        now = time.monotonic()
        async with self._lock:
            start, attempts = self._buckets.get(key, (now, 0))
            if now - start >= self._window:
                start, attempts = now, 0
            retry_after = max(1, int(self._window - (now - start)))
            if attempts >= self._attempts:
                return AuthRateDecision(False, retry_after)
            self._buckets[key] = (start, attempts + 1)
            return AuthRateDecision(True)

    async def clear(self, key: str) -> None:
        async with self._lock:
            self._buckets.pop(key, None)


class RedisAuthRateLimiter:
    """Distributed limiter used when the deployment provides REDIS_URL."""

    def __init__(self, settings: Settings, *, attempts: int | None = None) -> None:
        if not settings.redis_url:
            raise ValueError("REDIS_URL is required for Redis authentication rate limiting")
        self._url = settings.redis_url
        self._attempts = attempts or settings.auth_login_rate_limit_attempts
        self._window = settings.auth_rate_limit_window_seconds
        self._client = None

    async def _redis(self):
        if self._client is None:
            try:
                from redis.asyncio import from_url
            except ImportError as exc:
                raise RuntimeError(
                    "Install redis to enable distributed auth rate limiting"
                ) from exc
            self._client = from_url(self._url, decode_responses=True)
        return self._client

    async def check(self, key: str) -> AuthRateDecision:
        client = await self._redis()
        bucket = "lingua:auth:rate:" + hashlib.sha256(key.encode()).hexdigest()
        count = int(await client.incr(bucket))
        if count == 1:
            await client.expire(bucket, self._window)
        ttl = await client.ttl(bucket)
        if count > self._attempts:
            return AuthRateDecision(False, max(1, ttl))
        return AuthRateDecision(True)

    async def clear(self, key: str) -> None:
        client = await self._redis()
        bucket = "lingua:auth:rate:" + hashlib.sha256(key.encode()).hexdigest()
        await client.delete(bucket)


def _build_limiter(*, attempts: int | None = None):
    settings = get_settings()
    if settings.redis_url:
        return RedisAuthRateLimiter(settings, attempts=attempts)
    return InMemoryAuthRateLimiter(settings, attempts=attempts)


_auth_rate_limiter = _build_limiter()
_auth_action_rate_limiter = _build_limiter(
    attempts=get_settings().auth_action_rate_limit_attempts
)


def get_auth_rate_limiter() -> InMemoryAuthRateLimiter:
    return _auth_rate_limiter


def get_auth_action_rate_limiter() -> InMemoryAuthRateLimiter:
    return _auth_action_rate_limiter
