"""use clock_timestamp in set_updated_at

Revision ID: d7ec42908766
Revises: 3905480dfacd
Create Date: 2026-05-11 14:37:18.131349

"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "d7ec42908766"
down_revision: str | Sequence[str] | None = "3905480dfacd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION keystone.set_updated_at() RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = clock_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

def downgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION keystone.set_updated_at() RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
