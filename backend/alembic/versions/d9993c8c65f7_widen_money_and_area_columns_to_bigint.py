"""widen money and area columns to bigint

Revision ID: d9993c8c65f7
Revises: a0d5a957e619
Create Date: 2026-05-11 19:35:06.054827

"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa


revision: str = "d9993c8c65f7"
down_revision: str | Sequence[str] | None = "a0d5a957e619"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "properties",
        "current_assessed_total",
        type_=sa.BigInteger(),
        existing_nullable=True,
        schema="keystone",
    )
    op.alter_column(
        "properties",
        "current_assessed_land",
        type_=sa.BigInteger(),
        existing_nullable=True,
        schema="keystone",
    )
    op.alter_column(
        "properties",
        "current_assessed_building",
        type_=sa.BigInteger(),
        existing_nullable=True,
        schema="keystone",
    )
    op.alter_column(
        "properties",
        "square_feet_lot",
        type_=sa.BigInteger(),
        existing_nullable=True,
        schema="keystone",
    )
    op.alter_column(
        "properties",
        "last_sale_price",
        type_=sa.BigInteger(),
        existing_nullable=True,
        schema="keystone",
    )
    op.alter_column(
        "sales",
        "sale_price",
        type_=sa.BigInteger(),
        existing_nullable=False,
        schema="keystone",
    )


def downgrade() -> None:
    op.alter_column(
        "sales",
        "sale_price",
        type_=sa.Integer(),
        existing_nullable=False,
        schema="keystone",
    )
    op.alter_column(
        "properties",
        "last_sale_price",
        type_=sa.Integer(),
        existing_nullable=True,
        schema="keystone",
    )
    op.alter_column(
        "properties",
        "square_feet_lot",
        type_=sa.Integer(),
        existing_nullable=True,
        schema="keystone",
    )
    op.alter_column(
        "properties",
        "current_assessed_building",
        type_=sa.Integer(),
        existing_nullable=True,
        schema="keystone",
    )
    op.alter_column(
        "properties",
        "current_assessed_land",
        type_=sa.Integer(),
        existing_nullable=True,
        schema="keystone",
    )
    op.alter_column(
        "properties",
        "current_assessed_total",
        type_=sa.Integer(),
        existing_nullable=True,
        schema="keystone",
    )