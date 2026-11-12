from pydantic import BaseModel, ConfigDict, Field


class DocumentBlockResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    kind: str
    page: int | None = None
    location: str | None = None


class DocumentCapabilitiesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    formats: list[str]
    max_upload_bytes: int
    max_pages: int
    max_characters: int
    max_segment_characters: int
    ocr_fallback: bool


class DocumentExtractResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    format: str
    text: str
    blocks: list[DocumentBlockResponse]
    pages: int
    ocr_pages: list[int]
    segments: list[str] = Field(default_factory=list)
    request_id: str
