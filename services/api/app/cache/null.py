class NullTranslationCache:
    async def get(self, key: str) -> None:
        del key
        return None

    async def set(self, key: str, value: dict[str, object], ttl_seconds: int) -> None:
        del key, value, ttl_seconds
