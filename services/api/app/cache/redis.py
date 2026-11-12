import json


class RedisTranslationCache:
    def __init__(self, url: str):
        try:
            from redis.asyncio import Redis
        except ImportError as error:  # pragma: no cover - only used when explicitly enabled
            raise RuntimeError("Install redis to enable translation caching") from error
        self._client = Redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> dict[str, object] | None:
        value = await self._client.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        await self._client.set(key, json.dumps(value), ex=ttl_seconds)
