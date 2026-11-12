from __future__ import annotations

import asyncio
import importlib.util
import shutil
import subprocess
from typing import Any

from PIL import Image

from app.core.config import Settings
from app.providers.ocr.base import OCRBlock, OCRProvider, OCRProviderError, OCRResult
from app.providers.ocr.mapping import APPLICATION_TO_TESSERACT


def installed_tesseract_languages(command: str = "tesseract") -> frozenset[str]:
    """Return installed traineddata names without exposing command output to clients."""
    if shutil.which(command) is None:
        return frozenset()
    try:
        completed = subprocess.run(
            [command, "--list-langs"],
            check=False,
            capture_output=True,
            timeout=5,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    if completed.returncode != 0:
        return frozenset()
    return frozenset(
        line.strip()
        for line in completed.stdout.decode("utf-8", errors="replace").splitlines()
        if line.strip() and not line.lower().startswith("list of available")
    )


class TesseractOCRProvider(OCRProvider):
    name = "tesseract"

    def __init__(
        self,
        settings: Settings,
        *,
        installed_languages: frozenset[str] | None = None,
        pytesseract_module: Any | None = None,
    ) -> None:
        self._settings = settings
        self._pytesseract = pytesseract_module
        self._dependency_available = (
            pytesseract_module is not None or importlib.util.find_spec("pytesseract") is not None
        )
        self._installed = (
            installed_languages
            if installed_languages is not None
            else installed_tesseract_languages(settings.ocr_tesseract_command)
        )
        self.supported_languages = tuple(
            code
            for code, tess_code in APPLICATION_TO_TESSERACT.items()
            if self._dependency_available and tess_code in self._installed
        )

    @property
    def configured(self) -> bool:
        return bool(self.supported_languages)

    async def extract(self, *, image: Image.Image, language: str) -> OCRResult:
        tess_language = APPLICATION_TO_TESSERACT.get(language)
        if tess_language is None:
            raise OCRProviderError(
                "UNSUPPORTED_OCR_LANGUAGE", "Unsupported OCR language", status_code=422
            )
        if tess_language not in self._installed:
            raise OCRProviderError(
                "OCR_LANGUAGE_PACK_MISSING", "OCR language pack is not installed", status_code=503
            )
        pytesseract = self._pytesseract or self._load_pytesseract()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._extract_sync, pytesseract, image, tess_language),
                timeout=self._settings.ocr_timeout_seconds,
            )
        except TimeoutError as exc:
            raise OCRProviderError(
                "OCR_TIMEOUT", "OCR processing timed out", status_code=504
            ) from exc
        except OCRProviderError:
            raise
        except Exception as exc:
            raise OCRProviderError(
                "OCR_PROVIDER_ERROR", "OCR processing failed", status_code=502
            ) from exc
        return result

    def _load_pytesseract(self) -> Any:
        try:
            import pytesseract
        except ImportError as exc:
            raise OCRProviderError(
                "OCR_PROVIDER_DEPENDENCY_MISSING", "Tesseract OCR is unavailable", status_code=503
            ) from exc
        if self._settings.ocr_tesseract_command != "tesseract":
            pytesseract.pytesseract.tesseract_cmd = self._settings.ocr_tesseract_command
        return pytesseract

    def _extract_sync(self, pytesseract: Any, image: Image.Image, language: str) -> OCRResult:
        data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
        width, height = image.size
        blocks: list[OCRBlock] = []
        text_parts: list[str] = []
        for index, raw_text in enumerate(data.get("text", [])):
            text = str(raw_text).strip()
            if not text:
                continue
            left = max(0, int(data["left"][index]))
            top = max(0, int(data["top"][index]))
            box_width = max(0, int(data["width"][index]))
            box_height = max(0, int(data["height"][index]))
            try:
                confidence = float(data["conf"][index])
                if confidence < 0:
                    confidence = None
            except (KeyError, TypeError, ValueError):
                confidence = None
            blocks.append(
                OCRBlock(
                    text,
                    left / width,
                    top / height,
                    box_width / width,
                    box_height / height,
                    confidence,
                )
            )
            text_parts.append(text)
        return OCRResult(" ".join(text_parts), language, self.name, tuple(blocks))
