from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TranslationResult:
    translated_text: str
    provider: str
    detected_language: str | None = None


@dataclass(frozen=True)
class LanguageDetectionResult:
    language: str
    score: float
    alternatives: list[dict[str, object]]


class TranslationProviderError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 503,
        retry_after: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after


class TranslationProvider(ABC):
    name = "abstract"
    capabilities: frozenset[str] = frozenset()

    @abstractmethod
    async def translate(
        self, *, source_language: str | None, target_language: str, text: str
    ) -> TranslationResult:
        raise NotImplementedError

    @abstractmethod
    async def detect(self, *, text: str) -> LanguageDetectionResult:
        raise NotImplementedError
