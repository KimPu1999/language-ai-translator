from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    original_filename: str
    content_type: str
    document_format: str
    source_language: str | None
    size_bytes: int
    status: str
    progress: int
    page_count: int | None
    ocr_pages: list[int]
    error_code: str | None
    error_message: str | None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    target_language: str | None = None
    translation_characters: int = 0
    output_content_type: str | None = None
    output_filename: str | None = None


class DocumentSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    index: int
    source_text: str
    translated_text: str | None = None
    kind: str = "paragraph"
    page: int | None = None
    location: str | None = None
    block_index: int | None = None


class DocumentSegmentsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: UUID
    status: str
    segments: list[DocumentSegment]


class DocumentSegmentsUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    segments: list[DocumentSegment] = Field(min_length=1, max_length=100)


class DocumentTranslationRequest(BaseModel):
    source_language: str | None = Field(default=None, min_length=2, max_length=32)
    target_language: str = Field(min_length=2, max_length=32)
    reviewed: bool = False
