from app.providers.translation.azure import SUPPORTED_LANGUAGE_CODES
from app.providers.translation.base import TranslationProviderError, TranslationResult
from app.providers.translation.registry import TranslationProviderRegistry


class TranslationService:
    def __init__(self, registry: TranslationProviderRegistry):
        self.registry = registry

    async def translate(
        self, *, source_language: str | None, target_language: str, text: str
    ) -> TranslationResult:
        self._validate_language(target_language)
        if source_language is not None:
            self._validate_language(source_language)
        if source_language == target_language:
            raise TranslationProviderError(
                "INVALID_LANGUAGE_PAIR",
                "Source and target languages must be different",
                status_code=422,
            )
        provider = self.registry.get_for("text_translation")
        if provider is None:
            raise TranslationProviderError(
                "TRANSLATION_CAPABILITY_UNAVAILABLE"
                if self.registry.configured
                else "TRANSLATION_ENGINE_NOT_CONFIGURED",
                "Text translation capability is unavailable"
                if self.registry.configured
                else "Translation engine is not configured",
                status_code=503,
            )
        return await provider.translate(
            source_language=source_language, target_language=target_language, text=text
        )

    @staticmethod
    def _validate_language(language: str) -> None:
        if language not in SUPPORTED_LANGUAGE_CODES:
            raise TranslationProviderError(
                "UNSUPPORTED_LANGUAGE",
                f"Unsupported language: {language}",
                status_code=422,
            )
