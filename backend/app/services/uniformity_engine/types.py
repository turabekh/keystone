from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from uuid import UUID


class UniformitySignal(str, Enum):
    STRONG_CASE = "strong_case"
    MODERATE_CASE = "moderate_case"
    WEAK_CASE = "weak_case"
    NO_CASE = "no_case"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class NeighborhoodAsr:
    property_id: UUID
    address_full: str
    parcel_id: str
    sale_date: date
    sale_price: int
    assessment: int
    asr: float


@dataclass(frozen=True, slots=True)
class BlockUniformityResult:
    block_id: str
    median_asr: float
    sample_size: int
    asr_p25: float
    asr_p75: float
    samples: tuple[NeighborhoodAsr, ...]


@dataclass(frozen=True, slots=True)
class UniformityResult:
    subject_property_id: UUID
    subject_asr: float | None
    subject_asr_source: str
    neighborhood_median_asr: float | None
    neighborhood_sample_size: int
    block_result: BlockUniformityResult | None
    deviation_from_neighborhood: float | None
    deviation_from_block: float | None
    signal: UniformitySignal
    notes: tuple[str, ...] = field(default_factory=tuple)
    calculated_at: date | None = None