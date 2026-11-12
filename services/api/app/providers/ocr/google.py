from __future__ import annotations

import asyncio
import importlib.util
import json
from io import BytesIO
from typing import Any

from PIL import Image

from app.core.config import Settings
from app.providers.ocr.base import OCRBlock, OCRProvider, OCRProviderError, OCRResult
from app.providers.ocr.mapping import APPLICATION_TO_GOOGLE_VISION


class GoogleCloudVisionProvider(OCRProvider):
    name = "google-cloud-vision"
    supported_languages = tuple(APPLICATION_TO_GOOGLE_VISION)
    experimental_languages = ("my",)

    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
        vision_module: Any | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._vision = vision_module
        self._configured = client is not None
        if client is not None or not settings.ocr_google_cloud_enabled:
            return
        try:
            vision_available = importlib.util.find_spec("google.cloud.vision") is not None
        except ModuleNotFoundError:
            vision_available = False
        if not vision_available:
            return
        try:
            from google.cloud import vision

            credentials = None
            if settings.ocr_google_cloud_credentials_json:
                from google.oauth2 import service_account

                credentials = service_account.Credentials.from_service_account_info(
                    json.loads(settings.ocr_google_cloud_credentials_json.get_secret_value())
                )
            self._client = vision.ImageAnnotatorClient(credentials=credentials)
            self._configured = True
        except Exception:
            self._client = None
            self._configured = False

    @property
    def configured(self) -> bool:
        return self._configured

    async def extract(self, *, image: Image.Image, language: str) -> OCRResult:
        if language not in self.supported_languages:
            raise OCRProviderError(
                "UNSUPPORTED_OCR_LANGUAGE", "Unsupported OCR language", status_code=422
            )
        if not self._configured or self._client is None:
            raise OCRProviderError(
                "OCR_PROVIDER_NOT_CONFIGURED", "Google Cloud Vision is not configured"
            )
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._extract_sync, image, language),
                timeout=self._settings.ocr_timeout_seconds,
            )
        except TimeoutError as exc:
            raise OCRProviderError(
                "OCR_CLOUD_TIMEOUT", "Cloud OCR processing timed out", status_code=504
            ) from exc
        except OCRProviderError:
            raise
        except Exception as exc:
            code, status = self._map_cloud_error(exc)
            raise OCRProviderError(code, "Cloud OCR processing failed", status_code=status) from exc
        return result

    def _extract_sync(self, image: Image.Image, language: str) -> OCRResult:
        vision = self._vision
        if vision is None:
            from google.cloud import vision as imported_vision

            vision = imported_vision

        width, height = image.size
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        response = self._client.document_text_detection(
            image=vision.Image(content=buffer.getvalue()),
            image_context=vision.ImageContext(
                language_hints=[APPLICATION_TO_GOOGLE_VISION[language]]
            ),
        )
        if response.error and response.error.message:
            raise RuntimeError(response.error.message)
        annotation = response.full_text_annotation
        blocks: list[OCRBlock] = []
        for page in annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    text = "".join(
                        symbol.text for word in paragraph.words for symbol in word.symbols
                    ).strip()
                    if not text:
                        continue
                    left, top, right, bottom = self._bounds(
                        paragraph.bounding_box.vertices, width, height
                    )
                    blocks.append(
                        OCRBlock(
                            text,
                            left,
                            top,
                            right - left,
                            bottom - top,
                            float(paragraph.confidence) * 100,
                        )
                    )
        return OCRResult(annotation.text or "", language, self.name, tuple(blocks))

    @staticmethod
    def _bounds(vertices: Any, width: int, height: int) -> tuple[float, float, float, float]:
        xs = [max(0, min(width, int(getattr(vertex, "x", 0)))) for vertex in vertices]
        ys = [max(0, min(height, int(getattr(vertex, "y", 0)))) for vertex in vertices]
        if not xs or not ys:
            return 0, 0, 0, 0
        return min(xs) / width, min(ys) / height, max(xs) / width, max(ys) / height

    @staticmethod
    def _map_cloud_error(error: Exception) -> tuple[str, int]:
        message = str(error).lower()
        if any(
            token in message
            for token in ("permission", "unauthenticated", "invalid credential", "forbidden")
        ):
            return "OCR_CLOUD_AUTH_FAILED", 502
        if any(token in message for token in ("quota", "resource exhausted", "rate limit", "429")):
            return "OCR_CLOUD_QUOTA_EXCEEDED", 429
        return "OCR_CLOUD_PROVIDER_ERROR", 502
