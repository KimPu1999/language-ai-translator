from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.core.config import Settings
from app.providers.documents.base import DocumentExtractionError
from app.providers.documents.txt import TXTExtractor
from app.services.documents import (
    MAX_SEGMENT_CHARACTERS,
    DocumentExtractionService,
    segment_document_text,
)


def test_utf8_bom_and_myanmar_text_are_preserved():
    result = TXTExtractor().extract(BytesIO("\ufeffခရီးစဉ်\nEnglish".encode("utf-8")))
    assert result.text.startswith("ခရီးစဉ်")
    assert [block.kind for block in result.blocks] == ["paragraph", "paragraph"]


def test_invalid_txt_encoding_is_rejected():
    with pytest.raises(DocumentExtractionError, match="UTF-8"):
        TXTExtractor().extract(BytesIO(b"\xff\xfe\x00"))


def test_document_format_requires_real_signatures():
    service = DocumentExtractionService(settings=Settings())
    assert service.detect_format(b"%PDF-1.7\n", "file.bin", "application/pdf") == "pdf"
    with pytest.raises(DocumentExtractionError) as error:
        service.detect_format(
            b"PK-not-a-docx",
            "file.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    assert error.value.code == "INVALID_DOCUMENT_ARCHIVE"


def test_macro_and_zip_bomb_archives_are_rejected():
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "content")
        archive.writestr("word/document.xml", "document")
        archive.writestr("word/vbaProject.bin", "macro")
    service = DocumentExtractionService(settings=Settings())
    with pytest.raises(DocumentExtractionError) as error:
        service.detect_format(
            output.getvalue(),
            "file.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    assert error.value.code == "MACRO_DOCUMENT_UNSUPPORTED"


def test_text_segmentation_is_bounded_and_unicode_safe():
    text = "မ" * (MAX_SEGMENT_CHARACTERS + 1)
    segments = segment_document_text(text)
    assert len(segments) == 2
    assert all(len(segment) <= MAX_SEGMENT_CHARACTERS for segment in segments)
    assert "".join(segments) == text


def test_docx_extractor_handles_nested_tables_when_dependency_is_available():
    pytest.importorskip("docx")
    from docx import Document

    document = Document()
    document.add_paragraph("ခေါင်းစဉ်")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "outer"
    nested = table.cell(0, 0).add_table(rows=1, cols=1)
    nested.cell(0, 0).text = "inner"
    buffer = BytesIO()
    document.save(buffer)
    from app.providers.documents.docx import DOCXExtractor

    result = DOCXExtractor().extract(BytesIO(buffer.getvalue()))
    assert [block.text for block in result.blocks] == ["ခေါင်းစဉ်", "outer", "inner"]


def test_pdf_extractor_handles_digital_pdf_when_dependency_is_available():
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter

    from app.providers.documents.pdf import PDFTextExtractor

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = BytesIO()
    writer.write(buffer)
    result = PDFTextExtractor().extract(BytesIO(buffer.getvalue()))
    assert result.pages == 1
