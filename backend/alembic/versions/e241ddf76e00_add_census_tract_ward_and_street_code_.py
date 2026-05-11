"""add census tract ward and street code to properties

Revision ID: e241ddf76e00
Revises: a8be66e7901d
Create Date: 2026-05-11 22:14:16.106598

"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa


revision: str = "e241ddf76e00"
down_revision: str | Sequence[str] | None = "a8be66e7901d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "properties",
        sa.Column("census_tract", sa.String(20), nullable=True),
        schema="keystone",
    )
    op.add_column(
        "properties",
        sa.Column("geographic_ward", sa.String(10), nullable=True),
        schema="keystone",
    )
    op.add_column(
        "properties",
        sa.Column("street_code", sa.String(20), nullable=True),
        schema="keystone",
    )

    op.create_index(
        "ix_properties_census_tract",
        "properties",
        ["census_tract"],
        schema="keystone",
    )
    op.create_index(
        "ix_properties_geographic_ward",
        "properties",
        ["geographic_ward"],
        schema="keystone",
    )
    op.create_index(
        "ix_properties_street_code",
        "properties",
        ["street_code"],
        schema="keystone",
    )

    op.execute("""
        UPDATE keystone.properties
        SET 
            census_tract = NULLIF(raw_data->>'census_tract', ''),
            geographic_ward = NULLIF(raw_data->>'geographic_ward', ''),
            street_code = NULLIF(raw_data->>'street_code', '')
        WHERE source_id = 'philly_opa' AND raw_data IS NOT NULL;
    """)


def downgrade() -> None:
    op.drop_index("ix_properties_street_code", table_name="properties", schema="keystone")
    op.drop_index("ix_properties_geographic_ward", table_name="properties", schema="keystone")
    op.drop_index("ix_properties_census_tract", table_name="properties", schema="keystone")
    op.drop_column("properties", "street_code", schema="keystone")
    op.drop_column("properties", "geographic_ward", schema="keystone")
    op.drop_column("properties", "census_tract", schema="keystone")