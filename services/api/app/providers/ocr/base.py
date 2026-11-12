from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class OCRBlock:
    text: str
    left: float
    top: float
    width: float
    height: float
    confidence: float | None = None


@dataclass(frozen=True)
class OCRResult:
    text: str
    language: str
    provider: str
    blocks: tuple[OCRBlock, ...]


class OCRProviderError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class OCRProvider(ABC):
    name: str
    supported_languages: tuple[str, ...]

    @abstractmethod
    async def extract(self, *, image: object, language: str) -> OCRResult:
        raise NotImplementedError
