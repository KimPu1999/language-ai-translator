from dataclasses import dataclass

from app.services.document_export import TXTExporter, safe_output_filename
from app.services.documents import segment_document_blocks


@dataclass(frozen=True)
class Block:
    text: str
    kind: str = "paragraph"
    page: int | None = None
    location: str | None = None


def test_segments_keep_order_metadata_and_burmese_clusters():
    blocks = (Block("မင်္ဂလာပါ ကမ္ဘာ", page=2, location="p:2"), Block("Second", kind="heading"))
    segments = segment_document_blocks(blocks, limit=8)

    assert [segment["index"] for segment in segments] == list(range(len(segments)))
    assert segments[0]["id"] == "segment-0-0"
    assert segments[0]["page"] == 2
    assert all(len(segment["source_text"]) <= 8 for segment in segments)
    assert "".join(segment["source_text"] for segment in segments).startswith("မင်္ဂလာပါ")


def test_txt_export_preserves_unicode_and_segment_order():
    segments = [
        {"index": 1, "translated_text": "ဒုတိယ"},
        {"index": 0, "translated_text": "ပထမ"},
    ]
    assert TXTExporter().export(title="ignored", segments=segments).decode() == "ပထမ\n\nဒုတိယ"


def test_output_filename_does_not_use_untrusted_path_components():
    assert (
        safe_output_filename("../../private report?.pdf", "pdf")
        == "private-report-translated.pdf"
    )
