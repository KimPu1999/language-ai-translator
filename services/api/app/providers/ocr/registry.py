from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.providers.ocr.base import OCRProvider
from app.providers.ocr.google import GoogleCloudVisionProvider
from app.providers.ocr.tesseract import TesseractOCRProvider


@dataclass(frozen=True)
class OCRProviderRegistry:
    provider: OCRProvider | None
    languages: tuple[str, ...]
    experimental_languages: tuple[str, ...] = ()
    consent_required: bool = False

    @property
    def configured(self) -> bool:
        return self.provider is not None


class OCRProviderFactory:
    @staticmethod
    def create(settings: Settings) -> OCRProviderRegistry:
        if settings.ocr_provider == "google-cloud-vision":
            if not settings.ocr_google_cloud_enabled:
                return OCRProviderRegistry(None, ())
            google = GoogleCloudVisionProvider(settings)
            if google.configured:
                return OCRProviderRegistry(
                    google,
                    google.supported_languages,
                    google.experimental_languages,
                    True,
                )
            return OCRProviderRegistry(None, ())
        tesseract = TesseractOCRProvider(settings)
        if tesseract.configured:
            return OCRProviderRegistry(tesseract, tesseract.supported_languages)
        return OCRProviderRegistry(None, ())


def get_ocr_registry() -> OCRProviderRegistry:
    return OCRProviderFactory.create(get_settings())
