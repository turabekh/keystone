from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.services.comp_engine.types import (
    CompGeographicScope,
    ValuationConfidence,
)


class CompUsedRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    property_id: UUID
    address_full: str
    parcel_id: str
    sale_date: date
    sale_price: int
    sale_price_adjusted: int
    living_area: int | None
    price_per_sqft: float | None
    similarity_score: float
    geographic_scope: CompGeographicScope
    months_ago: int


class ValuationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_property_id: UUID
    point_estimate: int | None
    low_estimate: int | None
    high_estimate: int | None
    confidence: ValuationConfidence
    comp_count: int
    comps: list[CompUsedRead]
    notes: list[str]
    time_adjustment_rate_annual: float
    calculated_at: date | None