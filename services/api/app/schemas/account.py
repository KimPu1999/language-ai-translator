from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.text import character_count, normalize_text


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    email: EmailStr
    display_name: str | None
    email_verified: bool
    created_at: datetime


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("display_name", mode="before")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    locale: Literal["en", "my"]
    theme: Literal["light", "dark", "system"]
    history_enabled: bool
    sync_enabled: bool = False


class PreferencesUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locale: Literal["en", "my"] | None = None
    theme: Literal["light", "dark", "system"] | None = None
    history_enabled: bool | None = None
    sync_enabled: bool | None = None


class HistoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_language: Annotated[str, Field(min_length=2, max_length=32)]
    target_language: Annotated[str, Field(min_length=2, max_length=32)]
    source_text: Annotated[str, Field(min_length=1, max_length=5000)]
    translated_text: Annotated[str, Field(min_length=1, max_length=20_000)]
    provider: Annotated[str, Field(min_length=1, max_length=64)]

    @field_validator("source_text", "translated_text")
    @classmethod
    def normalize_translation_text(cls, value: str, info) -> str:
        normalized = normalize_text(value)
        if not normalized.strip():
            raise ValueError(f"{info.field_name} must not be blank")
        if info.field_name == "source_text" and character_count(normalized) > 5000:
            raise ValueError("source_text must be at most 5000 Unicode characters")
        return normalized

    @field_validator("source_language", "target_language", "provider")
    @classmethod
    def trim_metadata(cls, value: str) -> str:
        return value.strip()


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    source_language: str
    target_language: str
    source_text: str
    translated_text: str
    provider: str
    created_at: datetime


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


class FavoriteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    translation_id: UUID


class FavoriteItem(BaseModel):
    id: UUID
    translation_id: UUID
    created_at: datetime
    translation: HistoryItem


class FavoriteListResponse(BaseModel):
    items: list[FavoriteItem]
    total: int
    limit: int
    offset: int


class AccountDeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=1024)


class AccountMessageResponse(BaseModel):
    message: str
