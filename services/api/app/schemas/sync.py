# ruff: noqa: E501
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.text import character_count, normalize_text

SyncEntityType = Literal["translation", "favorite"]


class SyncConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class SyncRecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: SyncEntityType
    client_record_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    client_updated_at: datetime
    deleted: bool = False
    source_language: str | None = Field(default=None, min_length=2, max_length=32)
    target_language: str | None = Field(default=None, min_length=2, max_length=32)
    source_text: str | None = Field(default=None, max_length=5000)
    translated_text: str | None = Field(default=None, max_length=20000)
    provider: str | None = Field(default=None, max_length=64)
    translation_client_record_id: str | None = Field(default=None, max_length=128)

    @field_validator("source_text", "translated_text", mode="before")
    @classmethod
    def normalize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        result = normalize_text(value)
        if not result.strip():
            raise ValueError("text must not be blank")
        return result

    @field_validator("source_language", "target_language", "provider", "translation_client_record_id")
    @classmethod
    def trim_fields(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_entity(self) -> SyncRecordInput:
        if self.deleted:
            return self
        if self.entity_type == "translation":
            if not all((self.source_language, self.target_language, self.source_text, self.translated_text, self.provider)):
                raise ValueError("translation records require language, text, and provider fields")
            if character_count(self.source_text or "") > 5000:
                raise ValueError("source_text must be at most 5000 Unicode characters")
        elif not self.translation_client_record_id:
            raise ValueError("favorite records require translation_client_record_id")
        return self


class SyncPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[SyncRecordInput] = Field(min_length=1, max_length=50)


class SyncImportRequest(SyncPreviewRequest):
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class SyncRecordResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_type: SyncEntityType
    client_record_id: str
    server_record_id: UUID | None
    version: int
    client_updated_at: datetime
    updated_at: datetime
    deleted: bool
    source_language: str | None = None
    target_language: str | None = None
    source_text: str | None = None
    translated_text: str | None = None
    provider: str | None = None
    translation_client_record_id: str | None = None


class SyncPreviewItem(BaseModel):
    client_record_id: str
    entity_type: SyncEntityType
    accepted: bool
    reason: str | None = None


class SyncPreviewResponse(BaseModel):
    accepted_count: int
    rejected_count: int
    items: list[SyncPreviewItem]


class SyncImportItem(BaseModel):
    client_record_id: str
    entity_type: SyncEntityType
    status: Literal["applied", "ignored", "deleted", "rejected"]
    server_record_id: UUID | None = None
    version: int | None = None
    error_code: str | None = None


class SyncImportResponse(BaseModel):
    items: list[SyncImportItem]
    next_cursor: str | None = None


class SyncStatusResponse(BaseModel):
    enabled: bool
    server_time: datetime
    preferences: dict[str, str]


class SyncChangesResponse(BaseModel):
    items: list[SyncRecordResponse]
    next_cursor: str | None
    has_more: bool


class SyncPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locale: Literal["en", "my"] | None = None
    theme: Literal["light", "dark", "system"] | None = None
