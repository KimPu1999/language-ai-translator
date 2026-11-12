from app.providers.translation.azure import SUPPORTED_LANGUAGE_CODES
from app.providers.translation.base import LanguageDetectionResult, TranslationProviderError
from app.providers.translation.registry import TranslationProviderRegistry


class LanguageDetectionService:
    def __init__(self, registry: TranslationProviderRegistry):
        self.registry = registry

    async def detect(self, *, text: str) -> LanguageDetectionResult:
        provider = self.registry.get_for("language_detection")
        if provider is None:
            raise TranslationProviderError(
                "TRANSLATION_CAPABILITY_UNAVAILABLE"
                if self.registry.configured
                else "TRANSLATION_ENGINE_NOT_CONFIGURED",
                "Language detection capability is unavailable"
                if self.registry.configured
                else "Translation engine is not configured",
                status_code=503,
            )
        result = await provider.detect(text=text)
        if result.language not in SUPPORTED_LANGUAGE_CODES:
            raise TranslationProviderError(
                "UNSUPPORTED_LANGUAGE",
                f"Detected language is not supported: {result.language}",
                status_code=422,
            )
        return result
