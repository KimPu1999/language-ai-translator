"""add explicit private synchronization ledger"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010_private_sync"
down_revision = "0009_profiles_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("sync_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "sync_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=24), nullable=False),
        sa.Column("client_record_id", sa.String(length=128), nullable=False),
        sa.Column("server_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "entity_type", "client_record_id", name="uq_sync_records_client"
        ),
    )
    op.create_index("ix_sync_records_user_cursor", "sync_records", ["user_id", "updated_at", "id"])
    op.create_index("ix_sync_records_user_deleted", "sync_records", ["user_id", "deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_sync_records_user_deleted", table_name="sync_records")
    op.drop_index("ix_sync_records_user_cursor", table_name="sync_records")
    op.drop_table("sync_records")
    op.drop_column("user_preferences", "sync_enabled")
