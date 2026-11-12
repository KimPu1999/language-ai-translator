from pydantic import BaseModel, ConfigDict, Field


class OCRBlockResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    left: float = Field(ge=0, le=1)
    top: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=100)


class OCRCapabilitiesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str | None
    provider_configured: bool
    languages: list[str]
    experimental_languages: list[str] = Field(default_factory=list)
    consent_required: bool = False


class OCRExtractResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    language: str
    provider: str
    blocks: list[OCRBlockResponse]
    request_id: str
