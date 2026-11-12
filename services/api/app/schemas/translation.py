from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.core.text import character_count, normalize_text


class TextTranslationRequest(BaseModel):
    source_language: Annotated[str | None, Field(min_length=2, max_length=32)] = None
    target_language: Annotated[str, Field(min_length=2, max_length=32)]
    text: Annotated[str, Field(min_length=1)]

    @field_validator("text")
    @classmethod
    def validate_unicode_text(cls, value: str) -> str:
        value = normalize_text(value)
        if character_count(value) > 5000:
            raise ValueError("Text must be at most 5000 Unicode characters")
        return value


class TextTranslationResponse(BaseModel):
    translated_text: str
    provider: str
    detected_language: str | None = None
    request_id: str | None = None


class LanguageDetectionRequest(BaseModel):
    text: Annotated[str, Field(min_length=1)]

    @field_validator("text")
    @classmethod
    def validate_unicode_text(cls, value: str) -> str:
        value = normalize_text(value)
        if character_count(value) > 5000:
            raise ValueError("Text must be at most 5000 Unicode characters")
        return value


class LanguageDetectionResponse(BaseModel):
    language: str
    score: float
    alternatives: list[dict[str, object]] = Field(default_factory=list)
    request_id: str | None = None
