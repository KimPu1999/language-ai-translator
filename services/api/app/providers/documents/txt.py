from __future__ import annotations

from typing import BinaryIO

from app.providers.documents.base import (
    DocumentBlock,
    DocumentExtractionError,
    DocumentExtractor,
    ExtractedDocument,
)


class TXTExtractor(DocumentExtractor):
    format = "txt"

    def extract(self, stream: BinaryIO, *, source_language: str | None = None) -> ExtractedDocument:
        del source_language
        data = stream.read()
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError(
                "UNSUPPORTED_TEXT_ENCODING",
                "TXT files must be valid UTF-8 or UTF-8 with BOM",
            ) from exc
        if not text.strip():
            raise DocumentExtractionError("EMPTY_DOCUMENT", "The document contains no text")
        blocks = tuple(
            DocumentBlock(line, "paragraph", location=f"line:{index}")
            for index, line in enumerate(text.splitlines(), 1)
            if line.strip()
        )
        return ExtractedDocument(self.format, blocks, text, 1)
