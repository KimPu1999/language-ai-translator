from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.providers.speech.azure import (
    AzureSpeechRecognitionProvider,
    AzureSpeechSynthesisProvider,
)
from app.providers.speech.base import (
    SpeechLanguageCapability,
    SpeechRecognitionProvider,
    SpeechSynthesisProvider,
)
from app.providers.speech.mapping import SPEECH_LANGUAGE_CAPABILITIES


@dataclass(frozen=True)
class SpeechProviderRegistry:
    recognition: SpeechRecognitionProvider | None
    synthesis: SpeechSynthesisProvider | None
    capabilities: tuple[SpeechLanguageCapability, ...] = SPEECH_LANGUAGE_CAPABILITIES

    @property
    def configured(self) -> bool:
        return self.recognition is not None or self.synthesis is not None

    @property
    def recognition_configured(self) -> bool:
        return self.recognition is not None

    @property
    def synthesis_configured(self) -> bool:
        return self.synthesis is not None


class SpeechProviderFactory:
    @staticmethod
    def create(settings: Settings) -> SpeechProviderRegistry:
        if not settings.azure_speech_key or not settings.azure_speech_region:
            return SpeechProviderRegistry(recognition=None, synthesis=None)
        return SpeechProviderRegistry(
            recognition=AzureSpeechRecognitionProvider(settings),
            synthesis=AzureSpeechSynthesisProvider(settings),
        )


def get_speech_registry() -> SpeechProviderRegistry:
    return SpeechProviderFactory.create(get_settings())
