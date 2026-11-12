from typing import Protocol


class TranslationCache(Protocol):
    async def get(self, key: str) -> dict[str, object] | None: ...

    async def set(self, key: str, value: dict[str, object], ttl_seconds: int) -> None: ...
