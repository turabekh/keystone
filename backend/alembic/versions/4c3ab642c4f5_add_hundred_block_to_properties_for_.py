"""add hundred_block to properties for block-level comp matching

Revision ID: 4c3ab642c4f5
Revises: e241ddf76e00
Create Date: 2026-05-11 22:25:31.626217

"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "4c3ab642c4f5"
down_revision: str | Sequence[str] | None = "e241ddf76e00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "properties",
        sa.Column("hundred_block", sa.Integer(), nullable=True),
        schema="keystone",
    )

    op.execute("""
        UPDATE keystone.properties
        SET hundred_block = (FLOOR(CAST(NULLIF(street_number, '') AS INTEGER) / 100.0) * 100)::integer
        WHERE source_id = 'philly_opa'
          AND street_number IS NOT NULL
          AND street_number ~ '^[0-9]+$';
    """)

    op.create_index(
        "ix_properties_street_code_hundred_block",
        "properties",
        ["street_code", "hundred_block"],
        schema="keystone",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_properties_street_code_hundred_block",
        table_name="properties",
        schema="keystone",
    )
    op.drop_column("properties", "hundred_block", schema="keystone")
