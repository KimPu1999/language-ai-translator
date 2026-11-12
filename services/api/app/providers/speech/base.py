from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechVoice:
    name: str
    locale: str
    gender: str


@dataclass(frozen=True)
class SpeechLanguageCapability:
    text_code: str
    locale: str
    stt_enabled: bool
    tts_enabled: bool
    voices: tuple[SpeechVoice, ...]


@dataclass(frozen=True)
class SpeechRecognitionResult:
    text: str
    locale: str
    provider: str


@dataclass(frozen=True)
class SpeechSynthesisResult:
    audio_data: bytes
    locale: str
    voice: str
    provider: str


class SpeechProviderError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 503,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after


class SpeechRecognitionProvider(ABC):
    name: str
    capabilities: tuple[SpeechLanguageCapability, ...]

    @abstractmethod
    async def recognize(self, *, audio_data: bytes, locale: str) -> SpeechRecognitionResult:
        raise NotImplementedError


class SpeechSynthesisProvider(ABC):
    name: str
    capabilities: tuple[SpeechLanguageCapability, ...]

    @abstractmethod
    async def synthesize(
        self, *, text: str, locale: str, voice: str | None = None
    ) -> SpeechSynthesisResult:
        raise NotImplementedError
