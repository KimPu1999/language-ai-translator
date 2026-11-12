from app.providers.translation.base import (
    LanguageDetectionResult,
    TranslationProvider,
    TranslationProviderError,
    TranslationResult,
)


class GoogleTranslationProvider(TranslationProvider):
    """Reserved adapter seam; Google fallback is intentionally not enabled."""

    name = "google"
    capabilities = frozenset({"text_translation", "language_detection"})

    async def translate(
        self, *, source_language: str | None, target_language: str, text: str
    ) -> TranslationResult:
        del source_language, target_language, text
        raise TranslationProviderError(
            "GOOGLE_PROVIDER_NOT_CONFIGURED", "Google translation provider is not configured"
        )

    async def detect(self, *, text: str) -> LanguageDetectionResult:
        del text
        raise TranslationProviderError(
            "GOOGLE_PROVIDER_NOT_CONFIGURED", "Google translation provider is not configured"
        )
