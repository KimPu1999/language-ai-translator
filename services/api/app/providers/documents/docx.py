from __future__ import annotations

from typing import BinaryIO

from app.providers.documents.base import (
    DocumentBlock,
    DocumentExtractionError,
    DocumentExtractor,
    ExtractedDocument,
)


class DOCXExtractor(DocumentExtractor):
    format = "docx"

    def extract(self, stream: BinaryIO, *, source_language: str | None = None) -> ExtractedDocument:
        del source_language
        try:
            from docx import Document

            document = Document(stream)
            blocks: list[DocumentBlock] = []
            for block in _iter_body_blocks(document):
                blocks.extend(block)
            for section in document.sections:
                blocks.extend(_paragraph_blocks(section.header, "header"))
                blocks.extend(_paragraph_blocks(section.footer, "footer"))
            text = "\n\n".join(block.text for block in blocks if block.text.strip())
            if not text.strip():
                raise DocumentExtractionError("EMPTY_DOCUMENT", "The document contains no text")
            return ExtractedDocument(self.format, tuple(blocks), text, 1)
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError(
                "INVALID_DOCX", "The DOCX document could not be parsed"
            ) from exc


def _iter_body_blocks(document: object):
    from docx.document import Document as DocumentType
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    parent = document.element.body if isinstance(document, DocumentType) else document._tc
    for child in parent.iterchildren():
        if isinstance(child, CT_P):
            paragraph = Paragraph(child, parent)
            if paragraph.text.strip():
                yield [DocumentBlock(paragraph.text, "paragraph")]
        elif isinstance(child, CT_Tbl):
            table = Table(child, parent)
            yield _table_blocks(table)


def _table_blocks(table: object) -> list[DocumentBlock]:
    blocks: list[DocumentBlock] = []
    for row_number, row in enumerate(table.rows, 1):
        for column_number, cell in enumerate(row.cells, 1):
            cell_text = "\n".join(p.text for p in cell.paragraphs if p.text.strip()).strip()
            if cell_text:
                blocks.append(
                    DocumentBlock(
                        cell_text, "table_cell", location=f"row:{row_number},column:{column_number}"
                    )
                )
            for nested in cell.tables:
                blocks.extend(_table_blocks(nested))
    return blocks


def _paragraph_blocks(container: object, kind: str) -> list[DocumentBlock]:
    return [DocumentBlock(p.text, kind) for p in container.paragraphs if p.text.strip()]
