from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
from typing import Any, BinaryIO

from app.providers.documents.base import (
    DocumentBlock,
    DocumentExtractionError,
    DocumentExtractor,
    ExtractedDocument,
)


class PDFTextExtractor(DocumentExtractor):
    format = "pdf"

    def __init__(self, *, reader_factory: Callable[[BinaryIO], Any] | None = None) -> None:
        self._reader_factory = reader_factory

    def extract(self, stream: BinaryIO, *, source_language: str | None = None) -> ExtractedDocument:
        del source_language
        try:
            from pypdf import PdfReader

            reader = (self._reader_factory or PdfReader)(stream)
            if reader.is_encrypted:
                raise DocumentExtractionError(
                    "PASSWORD_PROTECTED_DOCUMENT", "Password-protected PDFs are not supported"
                )
            blocks: list[DocumentBlock] = []
            for page_number, page in enumerate(reader.pages, 1):
                text = (page.extract_text() or "").strip()
                if text:
                    blocks.append(DocumentBlock(text, "page", page_number))
            return ExtractedDocument(
                self.format, tuple(blocks), _join_blocks(blocks), len(reader.pages)
            )
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError("INVALID_PDF", "The PDF could not be parsed") from exc


class ScannedPDFExtractor(PDFTextExtractor):
    """PDF extractor that OCRs only pages without a usable text layer."""

    def __init__(
        self,
        ocr_registry: Any,
        *,
        reader_factory: Callable[[BinaryIO], Any] | None = None,
        renderer: Callable[[bytes, int], Any] | None = None,
    ) -> None:
        super().__init__(reader_factory=reader_factory)
        self._ocr_registry = ocr_registry
        self._renderer = renderer

    def extract(self, stream: BinaryIO, *, source_language: str | None = None) -> ExtractedDocument:
        data = stream.read()
        try:
            from pypdf import PdfReader

            reader = (self._reader_factory or PdfReader)(BytesIO(data))
            if reader.is_encrypted:
                raise DocumentExtractionError(
                    "PASSWORD_PROTECTED_DOCUMENT", "Password-protected PDFs are not supported"
                )
            blocks: list[DocumentBlock] = []
            ocr_pages: list[int] = []
            for page_number, page in enumerate(reader.pages, 1):
                text = (page.extract_text() or "").strip()
                if text:
                    blocks.append(DocumentBlock(text, "page", page_number))
                    continue
                if self._ocr_registry.provider is None or not source_language:
                    raise DocumentExtractionError(
                        "DOCUMENT_OCR_UNAVAILABLE",
                        "A source language and OCR provider are required for scanned pages",
                        status_code=503,
                    )
                image = self._render(data, page_number - 1)
                result = _run_ocr(self._ocr_registry.provider, image, source_language)
                if result.text.strip():
                    blocks.append(DocumentBlock(result.text.strip(), "ocr_page", page_number))
                    ocr_pages.append(page_number)
            return ExtractedDocument(
                self.format,
                tuple(blocks),
                _join_blocks(blocks),
                len(reader.pages),
                tuple(ocr_pages),
            )
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError("INVALID_PDF", "The PDF could not be parsed") from exc

    def _render(self, data: bytes, page_number: int) -> Any:
        if self._renderer:
            return self._renderer(data, page_number)
        try:
            import pypdfium2 as pdfium

            document = pdfium.PdfDocument(data)
            page = document.get_page(page_number)
            bitmap = page.render(scale=1.5)
            image = bitmap.to_pil()
            page.close()
            document.close()
            return image
        except Exception as exc:
            raise DocumentExtractionError(
                "PDF_RENDER_FAILED", "A scanned PDF page could not be rendered", status_code=422
            ) from exc


def _run_ocr(provider: Any, image: Any, language: str) -> Any:
    import asyncio

    return asyncio.run(provider.extract(image=image, language=language))


def _join_blocks(blocks: list[DocumentBlock] | tuple[DocumentBlock, ...]) -> str:
    return "\n\n".join(block.text for block in blocks if block.text.strip())
