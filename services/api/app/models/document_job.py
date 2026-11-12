from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentJob(Base):
    __tablename__ = "document_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'queued','extracting','awaiting_review','translating','exporting',"
            "'completed','failed','cancelled','expired')",
            name="ck_document_jobs_status",
        ),
        UniqueConstraint(
            "owner_subject", "idempotency_key", name="uq_document_jobs_owner_idempotency"
        ),
        Index("ix_document_jobs_owner_created_at", "owner_subject", "created_at"),
        Index("ix_document_jobs_status_expires_at", "status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_subject: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    document_format: Mapped[str] = mapped_column(String(16), nullable=False)
    source_language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    segments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_pages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    translation_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    translation_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    translation_characters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    translation_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    output_content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
