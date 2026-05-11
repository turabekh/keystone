"""create updated_at trigger function

Revision ID: f000f35cac1e
Revises:
Create Date: 2026-05-11 14:24:08.470738

"""

from collections.abc import Sequence
from alembic import op

revision: str = "f000f35cac1e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION keystone.set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS keystone.set_updated_at();")