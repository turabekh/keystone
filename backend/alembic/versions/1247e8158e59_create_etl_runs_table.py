"""create etl_runs table

Revision ID: 1247e8158e59
Revises: d71161fc307e
Create Date: 2026-05-11 15:00:04.898986

"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "1247e8158e59"
down_revision: str | Sequence[str] | None = "d71161fc307e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE keystone.etl_run_status AS ENUM ('running', 'success', 'failed', 'partial');
    """)

    op.create_table(
        "etl_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", postgresql.ENUM("running", "success", "failed", "partial", name="etl_run_status", schema="keystone", create_type=False), nullable=False),
        sa.Column("rows_seen", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_unchanged", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("source_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_etl_runs"),
        schema="keystone",
    )

    op.create_index("ix_etl_runs_source_id_started_at", "etl_runs", ["source_id", "started_at"], schema="keystone")
    op.create_index("ix_etl_runs_status", "etl_runs", ["status"], schema="keystone")

    op.execute("""
        CREATE TRIGGER trg_etl_runs_updated_at
        BEFORE UPDATE ON keystone.etl_runs
        FOR EACH ROW
        EXECUTE FUNCTION keystone.set_updated_at();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_etl_runs_updated_at ON keystone.etl_runs;")
    op.drop_index("ix_etl_runs_status", table_name="etl_runs", schema="keystone")
    op.drop_index("ix_etl_runs_source_id_started_at", table_name="etl_runs", schema="keystone")
    op.drop_table("etl_runs", schema="keystone")
    op.execute("DROP TYPE IF EXISTS keystone.etl_run_status;")