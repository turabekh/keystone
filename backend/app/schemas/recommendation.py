from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.services.recommendation_engine.types import (
    AppealArgument,
    AppealRecommendation,
    CounterAppealRisk,
    RecommendationConfidence,
)


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    subject_property_id: UUID
    recommendation: AppealRecommendation
    primary_argument: AppealArgument
    confidence: RecommendationConfidence
    
    current_assessment: int
    market_value_estimate: int | None
    appeal_target_assessment: int | None
    
    annual_tax_savings: int | None
    three_year_savings: int | None
    
    counter_appeal_risk: CounterAppealRisk
    
    reasoning: list[str]
    calculated_at: date | None