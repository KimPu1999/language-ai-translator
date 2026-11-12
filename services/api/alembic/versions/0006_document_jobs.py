"""add private document jobs and metadata-only usage events"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_document_jobs"
down_revision = "0005_ocr_cloud_billable_units"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_subject", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("document_format", sa.String(length=16), nullable=False),
        sa.Column("source_language", sa.String(length=32), nullable=True),
        sa.Column("storage_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("segments", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("ocr_pages", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ("
            "'queued','extracting','awaiting_review','translating','exporting',"
            "'completed','failed','cancelled','expired')",
            name="ck_document_jobs_status",
        ),
        sa.UniqueConstraint(
            "owner_subject", "idempotency_key", name="uq_document_jobs_owner_idempotency"
        ),
    )
    op.create_index(
        "ix_document_jobs_owner_created_at", "document_jobs", ["owner_subject", "created_at"]
    )
    op.create_index("ix_document_jobs_status_expires_at", "document_jobs", ["status", "expires_at"])
    op.create_table(
        "document_usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_subject", sa.String(length=128), nullable=False),
        sa.Column("document_format", sa.String(length=16), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("execution_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_document_usage_events_created_at", "document_usage_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_document_usage_events_created_at", table_name="document_usage_events")
    op.drop_table("document_usage_events")
    op.drop_index("ix_document_jobs_status_expires_at", table_name="document_jobs")
    op.drop_index("ix_document_jobs_owner_created_at", table_name="document_jobs")
    op.drop_table("document_jobs")
