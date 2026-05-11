from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class PropertyCategory(str, Enum):
    ROWHOUSE = "rowhouse"
    TWIN_SEMI = "twin_semi"
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    CONDO = "condo"
    MIXED_USE = "mixed_use"
    COMMERCIAL = "commercial"
    VACANT = "vacant"
    OTHER = "other"


class Property(BaseModel):
    __tablename__ = "properties"

    county_id: Mapped[UUID] = mapped_column(
        ForeignKey("counties.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parcel_id: Mapped[str] = mapped_column(String(50), nullable=False)

    address_full: Mapped[str] = mapped_column(String(500), nullable=False)
    address_normalized: Mapped[str] = mapped_column(String(500), nullable=False)

    street_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    street_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    street_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    street_suffix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    census_tract: Mapped[str | None] = mapped_column(String(20), nullable=True)
    geographic_ward: Mapped[str | None] = mapped_column(String(10), nullable=True)
    street_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hundred_block: Mapped[int | None] = mapped_column(Integer, nullable=True)

    property_category: Mapped[PropertyCategory] = mapped_column(
            ENUM(
                PropertyCategory,
                name="property_category",
                schema="keystone",
                create_type=False,
                values_callable=lambda enum: [e.value for e in enum],
            ),
            nullable=False,
        )
    source_property_type: Mapped[str | None] = mapped_column(String(200), nullable=True)

    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    square_feet_living: Mapped[int | None] = mapped_column(Integer, nullable=True)
    square_feet_lot: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    number_of_bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    number_of_bathrooms: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    number_of_stories: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)

    current_assessed_total: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_assessed_land: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_assessed_building: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_assessment_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    last_sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_sale_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)

    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    county: Mapped["County"] = relationship(back_populates="properties")

    sales: Mapped[list["Sale"]] = relationship(
        back_populates="property",
        cascade="all, delete-orphan",
        order_by="desc(Sale.sale_date)",
    )

    __table_args__ = (
        UniqueConstraint("county_id", "parcel_id", name="uq_properties_county_id_parcel_id"),
        CheckConstraint("state = upper(state)", name="ck_properties_state_uppercase"),
        CheckConstraint(
            "year_built IS NULL OR (year_built >= 1600 AND year_built <= 2100)",
            name="ck_properties_year_built_range",
        ),
        CheckConstraint(
            "current_assessed_total IS NULL OR current_assessed_total >= 0",
            name="ck_properties_assessed_nonnegative",
        ),
        CheckConstraint(
            "last_sale_price IS NULL OR last_sale_price >= 0",
            name="ck_properties_sale_price_nonnegative",
        ),
    )