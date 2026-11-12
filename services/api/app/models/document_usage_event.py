from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentUsageEvent(Base):
    __tablename__ = "document_usage_events"
    __table_args__ = (Index("ix_document_usage_events_created_at", "created_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_jobs.id", ondelete="CASCADE"), nullable=False
    )
    owner_subject: Mapped[str] = mapped_column(String(128), nullable=False)
    document_format: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    execution_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    operation: Mapped[str] = mapped_column(String(32), nullable=False, default="extraction")
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    characters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
