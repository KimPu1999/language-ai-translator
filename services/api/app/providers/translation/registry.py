from app.core.config import Settings, get_settings
from app.providers.translation.azure import AzureTranslationProvider
from app.providers.translation.base import TranslationProvider


class TranslationProviderRegistry:
    def __init__(self, providers: list[TranslationProvider] | None = None):
        self._providers = providers or []

    def get(self, _: str) -> TranslationProvider | None:
        return self._providers[0] if self._providers else None

    def get_for(self, operation: str) -> TranslationProvider | None:
        return next(
            (provider for provider in self._providers if operation in provider.capabilities),
            None,
        )

    @property
    def supported_operations(self) -> frozenset[str]:
        return frozenset().union(*(provider.capabilities for provider in self._providers))

    @property
    def configured(self) -> bool:
        return bool(self._providers)


class TranslationProviderFactory:
    @staticmethod
    def create(settings: Settings) -> TranslationProviderRegistry:
        if not settings.azure_translator_key:
            return TranslationProviderRegistry()
        return TranslationProviderRegistry([AzureTranslationProvider(settings)])


def get_translation_registry() -> TranslationProviderRegistry:
    return TranslationProviderFactory.create(get_settings())
