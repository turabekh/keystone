"""add clr ratio effective tax rate and sample size to county settings

Revision ID: 29feceb4dc34
Revises: d9993c8c65f7
Create Date: 2026-05-11 20:39:08.869511

"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "29feceb4dc34"
down_revision: str | Sequence[str] | None = "d9993c8c65f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "county_year_settings",
        sa.Column("clr_ratio", sa.Numeric(8, 4), nullable=True),
        schema="keystone",
    )
    op.add_column(
        "county_year_settings",
        sa.Column("effective_tax_rate", sa.Numeric(8, 6), nullable=True),
        schema="keystone",
    )
    op.add_column(
        "county_year_settings",
        sa.Column("clr_sample_size", sa.Integer(), nullable=True),
        schema="keystone",
    )
    op.add_column(
        "county_year_settings",
        sa.Column("clr_source_note", sa.String(500), nullable=True),
        schema="keystone",
    )

    op.create_check_constraint(
        "ck_county_year_settings_clr_ratio_range",
        "county_year_settings",
        "clr_ratio IS NULL OR (clr_ratio > 0 AND clr_ratio <= 100)",
        schema="keystone",
    )
    op.create_check_constraint(
        "ck_county_year_settings_effective_tax_rate_range",
        "county_year_settings",
        "effective_tax_rate IS NULL OR (effective_tax_rate > 0 AND effective_tax_rate < 1)",
        schema="keystone",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_county_year_settings_ck_county_year_settings_effective_tax_rate_range",
        "county_year_settings",
        schema="keystone",
    )
    op.drop_constraint(
        "ck_county_year_settings_ck_county_year_settings_clr_ratio_range",
        "county_year_settings",
        schema="keystone",
    )
    op.drop_column("county_year_settings", "clr_source_note", schema="keystone")
    op.drop_column("county_year_settings", "clr_sample_size", schema="keystone")
    op.drop_column("county_year_settings", "effective_tax_rate", schema="keystone")
    op.drop_column("county_year_settings", "clr_ratio", schema="keystone")