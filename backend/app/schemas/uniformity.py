from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.services.uniformity_engine.types import UniformitySignal


class NeighborhoodAsrRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    property_id: UUID
    address_full: str
    parcel_id: str
    sale_date: date
    sale_price: int
    assessment: int
    asr: float


class BlockUniformityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    block_id: str
    median_asr: float
    sample_size: int
    asr_p25: float
    asr_p75: float
    samples: list[NeighborhoodAsrRead]


class UniformityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    subject_property_id: UUID
    subject_asr: float | None
    subject_asr_source: str
    neighborhood_median_asr: float | None
    neighborhood_sample_size: int
    block_result: BlockUniformityRead | None
    deviation_from_neighborhood: float | None
    deviation_from_block: float | None
    signal: UniformitySignal
    notes: list[str]
    calculated_at: date | None