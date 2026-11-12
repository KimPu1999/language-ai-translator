# ruff: noqa: E501
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncRecord(Base):
    """Per-user synchronization ledger, including delete tombstones.

    Payloads contain only explicitly opted-in translation/favorite metadata.  No
    audio, images, or documents are accepted by the API backed by this table.
    """

    __tablename__ = "sync_records"
    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "client_record_id", name="uq_sync_records_client"),
        Index("ix_sync_records_user_cursor", "user_id", "updated_at", "id"),
        Index("ix_sync_records_user_deleted", "user_id", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    client_record_id: Mapped[str] = mapped_column(String(128), nullable=False)
    server_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    client_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


__all__ = ["SyncRecord"]
