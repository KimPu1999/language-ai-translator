from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from app.core.config import Settings
from app.providers.documents.base import DocumentExtractionError, ExtractedDocument
from app.providers.documents.docx import DOCXExtractor
from app.providers.documents.pdf import PDFTextExtractor, ScannedPDFExtractor
from app.providers.documents.txt import TXTExtractor

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_PAGES = 30
MAX_DOCUMENT_CHARACTERS = 50_000
MAX_SEGMENT_CHARACTERS = 3_000


@dataclass(frozen=True)
class DocumentFormat:
    name: str
    media_types: tuple[str, ...]


SUPPORTED_FORMATS = {
    "pdf": DocumentFormat("pdf", ("application/pdf",)),
    "docx": DocumentFormat(
        "docx", ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",)
    ),
    "txt": DocumentFormat("txt", ("text/plain", "application/octet-stream")),
}


class DocumentExtractionService:
    def __init__(
        self, *, ocr_registry: object | None = None, settings: Settings | None = None
    ) -> None:
        self._ocr_registry = ocr_registry
        limits = settings or Settings()
        self._max_bytes = limits.document_max_upload_bytes
        self._max_pages = limits.document_max_pages
        self._max_characters = limits.document_max_characters
        self._max_segment_characters = limits.document_max_segment_characters

    def detect_format(self, data: bytes, filename: str, content_type: str | None) -> str:
        if not data:
            raise DocumentExtractionError("EMPTY_DOCUMENT", "The document is empty")
        if len(data) > self._max_bytes:
            raise DocumentExtractionError(
                "DOCUMENT_TOO_LARGE", "Documents must be 10 MB or smaller", status_code=413
            )
        lower = filename.lower()
        if data.startswith(b"%PDF-"):
            detected = "pdf"
        elif data[:2] == b"PK":
            detected = self._detect_zip_document(data)
        else:
            detected = (
                "txt"
                if lower.endswith(".txt") or content_type in SUPPORTED_FORMATS["txt"].media_types
                else None
            )
        if detected is None:
            raise DocumentExtractionError(
                "UNSUPPORTED_DOCUMENT_FORMAT", "Only PDF, DOCX, and UTF-8 TXT files are supported"
            )
        expected_types = SUPPORTED_FORMATS[detected].media_types
        if (
            content_type
            and content_type not in expected_types
            and not (detected == "txt" and content_type == "application/octet-stream")
        ):
            raise DocumentExtractionError(
                "DOCUMENT_SIGNATURE_MISMATCH", "The file type does not match its content"
            )
        return detected

    def extract(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str | None,
        source_language: str | None = None,
    ) -> ExtractedDocument:
        document_format = self.detect_format(data, filename, content_type)
        stream = io.BytesIO(data)
        if document_format == "pdf":
            extractor = (
                ScannedPDFExtractor(self._ocr_registry)
                if self._ocr_registry
                else PDFTextExtractor()
            )
        elif document_format == "docx":
            self._validate_docx_archive(data)
            extractor = DOCXExtractor()
        else:
            extractor = TXTExtractor()
        result = extractor.extract(stream, source_language=source_language)
        if result.pages > self._max_pages:
            raise DocumentExtractionError(
                "DOCUMENT_TOO_MANY_PAGES", "Documents are limited to 30 pages", status_code=413
            )
        if not result.text.strip():
            raise DocumentExtractionError(
                "EMPTY_DOCUMENT", "The document contains no extractable text"
            )
        if len(result.text) > self._max_characters:
            raise DocumentExtractionError(
                "DOCUMENT_TEXT_TOO_LARGE",
                "Extracted text exceeds the 50,000 character limit",
                status_code=413,
            )
        return result

    @staticmethod
    def _detect_zip_document(data: bytes) -> str | None:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())
                if any(name.lower().endswith("vbaproject.bin") for name in names):
                    raise DocumentExtractionError(
                        "MACRO_DOCUMENT_UNSUPPORTED", "Macro-enabled documents are not supported"
                    )
                if "[Content_Types].xml" in names and "word/document.xml" in names:
                    return "docx"
        except DocumentExtractionError:
            raise
        except (zipfile.BadZipFile, OSError) as exc:
            raise DocumentExtractionError(
                "INVALID_DOCUMENT_ARCHIVE", "The document archive is invalid"
            ) from exc
        return None

    @staticmethod
    def _validate_docx_archive(data: bytes) -> None:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                infos = archive.infolist()
                total_uncompressed = sum(info.file_size for info in infos)
                if len(infos) > 500 or total_uncompressed > 50 * 1024 * 1024:
                    raise DocumentExtractionError(
                        "DOCUMENT_ARCHIVE_TOO_LARGE",
                        "The document archive exceeds safe parsing limits",
                        status_code=413,
                    )
                for info in infos:
                    if info.compress_size and info.file_size / info.compress_size > 1000:
                        raise DocumentExtractionError(
                            "DOCUMENT_ARCHIVE_BOMB",
                            "The document archive compression ratio is unsafe",
                            status_code=413,
                        )
        except DocumentExtractionError:
            raise
        except (zipfile.BadZipFile, OSError) as exc:
            raise DocumentExtractionError(
                "INVALID_DOCUMENT_ARCHIVE", "The document archive is invalid"
            ) from exc


def segment_document_text(text: str, *, limit: int = MAX_SEGMENT_CHARACTERS) -> tuple[str, ...]:
    if limit <= 0:
        raise ValueError("segment limit must be positive")
    normalized = " ".join(text.split())
    return tuple(_grapheme_chunks(normalized, limit))


def segment_document_blocks(
    blocks: tuple[object, ...], *, limit: int = MAX_SEGMENT_CHARACTERS
) -> tuple[dict, ...]:
    """Create stable reviewable segments without splitting Unicode clusters."""
    if limit <= 0:
        raise ValueError("segment limit must be positive")
    output: list[dict] = []
    for block_index, block in enumerate(blocks):
        text = " ".join(str(block.text).split())
        for part, chunk in enumerate(_grapheme_chunks(text, limit)):
            output.append({
                "id": f"segment-{block_index}-{part}",
                "index": len(output),
                "source_text": chunk,
                "translated_text": None,
                "kind": getattr(block, "kind", "paragraph"),
                "page": getattr(block, "page", None),
                "location": getattr(block, "location", None),
                "block_index": block_index,
            })
    return tuple(output)


def normalize_document_segments(segments: list | None) -> list[dict]:
    """Upgrade Phase 5B string segments to the Phase 5C review shape."""
    normalized: list[dict] = []
    for index, item in enumerate(segments or []):
        if isinstance(item, str):
            normalized.append(
                {
                    "id": f"segment-{index}-0",
                    "index": index,
                    "source_text": item,
                    "translated_text": None,
                    "kind": "paragraph",
                    "page": None,
                    "location": None,
                    "block_index": index,
                }
            )
        elif isinstance(item, dict):
            value = dict(item)
            value.setdefault("id", f"segment-{index}-0")
            value.setdefault("index", index)
            value.setdefault("source_text", "")
            value.setdefault("translated_text", None)
            value.setdefault("kind", "paragraph")
            normalized.append(value)
    return normalized


def _grapheme_chunks(text: str, limit: int) -> list[str]:
    # Keep combining marks, variation selectors and ZWJ emoji sequences attached
    # to their base character. This avoids splitting Burmese syllables in normal
    # text without requiring a native extension in worker environments.
    import unicodedata

    clusters: list[str] = []
    for char in text:
        if clusters and (unicodedata.combining(char) or char in "\ufe0e\ufe0f"):
            clusters[-1] += char
        elif clusters and clusters[-1].endswith("\u200d"):
            clusters[-1] += char
        else:
            clusters.append(char)
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for cluster in clusters:
        if current and size + len(cluster) > limit:
            chunks.append("".join(current))
            current, size = [], 0
        current.append(cluster)
        size += len(cluster)
    if current:
        chunks.append("".join(current))
    return chunks
