from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID


class ValuationConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


class CompGeographicScope(str, Enum):
    SAME_BLOCK = "same_block"
    SAME_CENSUS_TRACT = "same_census_tract"
    SAME_WARD = "same_ward"


@dataclass(frozen=True, slots=True)
class CompUsed:
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


@dataclass(frozen=True, slots=True)
class ValuationResult:
    subject_property_id: UUID
    point_estimate: int | None
    low_estimate: int | None
    high_estimate: int | None
    confidence: ValuationConfidence
    comp_count: int
    comps: tuple[CompUsed, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    time_adjustment_rate_annual: float = 0.0
    calculated_at: date | None = None