from __future__ import annotations

import io
import re
from pathlib import Path

from app.providers.documents.base import DocumentExtractionError


def _text(segments: list[dict]) -> list[dict]:
    return sorted(segments, key=lambda item: item.get("index", 0))


class DocumentExporter:
    content_type: str
    extension: str

    def export(self, *, title: str, segments: list[dict]) -> bytes:
        raise NotImplementedError


class TXTExporter(DocumentExporter):
    content_type = "text/plain; charset=utf-8"
    extension = "txt"

    def export(self, *, title: str, segments: list[dict]) -> bytes:
        del title
        text = "\n\n".join(item.get("translated_text") or "" for item in _text(segments))
        return text.encode("utf-8")


class DOCXExporter(DocumentExporter):
    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    extension = "docx"

    def export(self, *, title: str, segments: list[dict]) -> bytes:
        try:
            from docx import Document
            from docx.shared import Pt
        except ImportError as exc:
            raise DocumentExtractionError(
                "EXPORT_PROVIDER_UNAVAILABLE", "DOCX export is unavailable", status_code=503
            ) from exc
        document = Document()
        document.add_heading(title, level=1)
        table_rows: dict[str, list[dict]] = {}
        for item in _text(segments):
            translated = item.get("translated_text") or ""
            if item.get("kind") == "table_cell" and item.get("location"):
                row = re.search(r"row:(\d+),column:(\d+)", item["location"])
                if row:
                    table_rows.setdefault(row.group(1), []).append((int(row.group(2)), translated))
                    continue
            paragraph = document.add_paragraph(translated)
            if item.get("kind") in {"heading", "title"}:
                paragraph.style = "Heading 2"
        if table_rows:
            columns = max(len(values) for values in table_rows.values())
            table = document.add_table(rows=len(table_rows), cols=columns)
            for r, values in enumerate(table_rows.values()):
                for c, value in sorted(values):
                    if c <= columns:
                        table.cell(r, c - 1).text = value
        for paragraph in document.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(11)
        output = io.BytesIO()
        document.save(output)
        return output.getvalue()


class PDFExporter(DocumentExporter):
    content_type = "application/pdf"
    extension = "pdf"

    def export(self, *, title: str, segments: list[dict]) -> bytes:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError as exc:
            raise DocumentExtractionError(
                "EXPORT_PROVIDER_UNAVAILABLE", "PDF export is unavailable", status_code=503
            ) from exc
        output = io.BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        font_path = _pdf_font_path()
        has_non_ascii = any(
            any(ord(char) > 127 for char in (item.get("translated_text") or ""))
            for item in segments
        )
        if has_non_ascii and not font_path:
            raise DocumentExtractionError(
                "EXPORT_UNICODE_FONT_UNAVAILABLE",
                "Configure a Unicode font before exporting multilingual PDF text",
                status_code=503,
            )
        if font_path:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            pdfmetrics.registerFont(TTFont("LinguaUnicode", font_path))
            styles["Title"].fontName = "LinguaUnicode"
            styles["BodyText"].fontName = "LinguaUnicode"
        story = [Paragraph(title, styles["Title"]), Spacer(1, 8)]
        table_values: list[list[str]] = []
        for item in _text(segments):
            value = item.get("translated_text") or ""
            value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if item.get("kind") == "table_cell":
                table_values.append([value])
            else:
                if table_values:
                    story.append(
                        Table(
                            table_values,
                            style=TableStyle(
                                [["GRID", (0, 0), (-1, -1), 0.5, "#cccccc"]]
                            ),
                        )
                    )
                    table_values = []
                story.append(Paragraph(value.replace("\n", "<br/>") or " ", styles["BodyText"]))
                story.append(Spacer(1, 5))
        if table_values:
            story.append(
                Table(
                    table_values,
                    style=TableStyle([["GRID", (0, 0), (-1, -1), 0.5, "#cccccc"]]),
                )
            )
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Page {doc.page}")
            canvas.restoreState()
        document.build(story, onFirstPage=footer, onLaterPages=footer)
        return output.getvalue()


def exporter_for(document_format: str) -> DocumentExporter:
    exporters = {"txt": TXTExporter(), "docx": DOCXExporter(), "pdf": PDFExporter()}
    return exporters.get(document_format, TXTExporter())


def _pdf_font_path() -> str | None:
    from app.core.config import get_settings

    candidates = [
        get_settings().document_pdf_font_path,
        # Common production/development locations for a Unicode Myanmar-capable
        # font. The explicit setting remains the portable deployment contract.
        "/usr/share/fonts/truetype/noto/NotoSansMyanmar-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansMyanmar-Regular.ttf",
        "/System/Library/Fonts/NotoSansMyanmar.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    return next((path for path in candidates if path and Path(path).is_file()), None)


def safe_output_filename(original: str, extension: str) -> str:
    stem = Path(original).stem or "translated-document"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-") or "translated-document"
    return f"{stem}-translated.{extension}"
