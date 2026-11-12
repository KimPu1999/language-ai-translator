"""add document translation and export metadata"""

import sqlalchemy as sa

from alembic import op

revision = "0007_document_translation"
down_revision = "0006_document_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_jobs", sa.Column("target_language", sa.String(32), nullable=True))
    op.add_column(
        "document_jobs", sa.Column("translation_idempotency_key", sa.String(128), nullable=True)
    )
    op.add_column("document_jobs", sa.Column("translation_provider", sa.String(64), nullable=True))
    op.add_column(
        "document_jobs",
        sa.Column("translation_characters", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("document_jobs", sa.Column("translation_task_id", sa.String(255), nullable=True))
    op.add_column("document_jobs", sa.Column("output_storage_key", sa.String(255), nullable=True))
    op.add_column("document_jobs", sa.Column("output_content_type", sa.String(128), nullable=True))
    op.add_column("document_jobs", sa.Column("output_filename", sa.String(255), nullable=True))
    op.create_unique_constraint(
        "uq_document_jobs_output_storage_key", "document_jobs", ["output_storage_key"]
    )
    op.add_column(
        "document_usage_events",
        sa.Column("operation", sa.String(32), nullable=False, server_default="extraction"),
    )
    op.add_column("document_usage_events", sa.Column("provider", sa.String(64), nullable=True))
    op.add_column(
        "document_usage_events",
        sa.Column("characters", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("document_usage_events", "characters")
    op.drop_column("document_usage_events", "provider")
    op.drop_column("document_usage_events", "operation")
    op.drop_constraint("uq_document_jobs_output_storage_key", "document_jobs", type_="unique")
    columns = (
        "output_filename", "output_content_type", "output_storage_key",
        "translation_task_id", "translation_characters", "translation_provider",
        "translation_idempotency_key", "target_language",
    )
    for column in columns:
        op.drop_column("document_jobs", column)
