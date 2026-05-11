"""create properties and sales tables

Revision ID: a0d5a957e619
Revises: 1247e8158e59
Create Date: 2026-05-11 15:36:13.305671

"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a0d5a957e619"
down_revision: str | Sequence[str] | None = "1247e8158e59"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE keystone.property_category AS ENUM (
            'rowhouse', 'twin_semi', 'single_family', 'multi_family',
            'condo', 'mixed_use', 'commercial', 'vacant', 'other'
        );
    """)

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("county_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parcel_id", sa.String(50), nullable=False),
        sa.Column("address_full", sa.String(500), nullable=False),
        sa.Column("address_normalized", sa.String(500), nullable=False),
        sa.Column("street_number", sa.String(20), nullable=True),
        sa.Column("street_direction", sa.String(10), nullable=True),
        sa.Column("street_name", sa.String(200), nullable=True),
        sa.Column("street_suffix", sa.String(20), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("zip_code", sa.String(10), nullable=True),
        sa.Column("property_category", postgresql.ENUM("rowhouse", "twin_semi", "single_family", "multi_family", "condo", "mixed_use", "commercial", "vacant", "other", name="property_category", schema="keystone", create_type=False), nullable=False),
        sa.Column("source_property_type", sa.String(200), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("square_feet_living", sa.Integer(), nullable=True),
        sa.Column("square_feet_lot", sa.Integer(), nullable=True),
        sa.Column("number_of_bedrooms", sa.Integer(), nullable=True),
        sa.Column("number_of_bathrooms", sa.Numeric(4, 1), nullable=True),
        sa.Column("number_of_stories", sa.Numeric(3, 1), nullable=True),
        sa.Column("current_assessed_total", sa.Integer(), nullable=True),
        sa.Column("current_assessed_land", sa.Integer(), nullable=True),
        sa.Column("current_assessed_building", sa.Integer(), nullable=True),
        sa.Column("current_assessment_year", sa.Integer(), nullable=True),
        sa.Column("last_sale_date", sa.Date(), nullable=True),
        sa.Column("last_sale_price", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["county_id"], ["keystone.counties.id"], name="fk_properties_county_id_counties", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_properties"),
        sa.UniqueConstraint("county_id", "parcel_id", name="uq_properties_county_id_parcel_id"),
        sa.CheckConstraint("state = upper(state)", name="ck_properties_state_uppercase"),
        sa.CheckConstraint("year_built IS NULL OR (year_built >= 1600 AND year_built <= 2100)", name="ck_properties_year_built_range"),
        sa.CheckConstraint("current_assessed_total IS NULL OR current_assessed_total >= 0", name="ck_properties_assessed_nonnegative"),
        sa.CheckConstraint("last_sale_price IS NULL OR last_sale_price >= 0", name="ck_properties_sale_price_nonnegative"),
        schema="keystone",
    )

    op.create_index("ix_properties_county_id", "properties", ["county_id"], schema="keystone")
    op.create_index("ix_properties_parcel_id", "properties", ["parcel_id"], schema="keystone")
    op.create_index("ix_properties_zip_code", "properties", ["zip_code"], schema="keystone")
    op.create_index("ix_properties_property_category", "properties", ["property_category"], schema="keystone")

    op.execute("""
        CREATE INDEX ix_properties_address_normalized_trgm
        ON keystone.properties
        USING gin (address_normalized gin_trgm_ops);
    """)

    op.execute("""
        CREATE INDEX ix_properties_street_name_trgm
        ON keystone.properties
        USING gin (street_name gin_trgm_ops);
    """)

    op.execute("""
        CREATE TRIGGER trg_properties_updated_at
        BEFORE UPDATE ON keystone.properties
        FOR EACH ROW
        EXECUTE FUNCTION keystone.set_updated_at();
    """)

    op.create_table(
        "sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("sale_price", sa.Integer(), nullable=False),
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("deed_type", sa.String(100), nullable=True),
        sa.Column("grantor", sa.String(500), nullable=True),
        sa.Column("grantee", sa.String(500), nullable=True),
        sa.Column("is_arms_length", sa.Boolean(), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["keystone.properties.id"], name="fk_sales_property_id_properties", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_sales"),
        sa.CheckConstraint("sale_price >= 0", name="ck_sales_price_nonnegative"),
        schema="keystone",
    )

    op.create_index("ix_sales_property_id", "sales", ["property_id"], schema="keystone")
    op.create_index("ix_sales_sale_date", "sales", ["sale_date"], schema="keystone")
    op.create_index("ix_sales_property_id_sale_date", "sales", ["property_id", "sale_date"], schema="keystone")

    op.execute("""
        CREATE UNIQUE INDEX uq_sales_source_id_document_number
        ON keystone.sales (source_id, document_number)
        WHERE document_number IS NOT NULL;
    """)

    op.execute("""
        CREATE TRIGGER trg_sales_updated_at
        BEFORE UPDATE ON keystone.sales
        FOR EACH ROW
        EXECUTE FUNCTION keystone.set_updated_at();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_sales_updated_at ON keystone.sales;")
    op.drop_table("sales", schema="keystone")
    op.execute("DROP TRIGGER IF EXISTS trg_properties_updated_at ON keystone.properties;")
    op.drop_table("properties", schema="keystone")
    op.execute("DROP TYPE IF EXISTS keystone.property_category;")