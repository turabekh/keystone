from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.property import PropertyCategory


class PropertyLookupResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parcel_id: str
    address_full: str
    zip_code: str | None
    property_category: PropertyCategory
    current_assessed_total: int | None
    similarity: float = Field(description="Trigram similarity 0.0-1.0")


class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sale_date: date
    sale_price: int
    deed_type: str | None
    grantor: str | None
    grantee: str | None
    is_arms_length: bool | None


class PropertyDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    county_id: UUID
    parcel_id: str

    address_full: str
    address_normalized: str
    street_number: str | None
    street_direction: str | None
    street_name: str | None
    street_suffix: str | None
    unit: str | None
    city: str | None
    state: str
    zip_code: str | None

    property_category: PropertyCategory
    source_property_type: str | None

    year_built: int | None
    square_feet_living: int | None
    square_feet_lot: int | None
    number_of_bedrooms: int | None
    number_of_bathrooms: Decimal | None
    number_of_stories: Decimal | None

    current_assessed_total: int | None
    current_assessed_land: int | None
    current_assessed_building: int | None
    current_assessment_year: int | None

    last_sale_date: date | None
    last_sale_price: int | None

    source_id: str
    created_at: datetime
    updated_at: datetime

    sales: list[SaleRead] = Field(default_factory=list)