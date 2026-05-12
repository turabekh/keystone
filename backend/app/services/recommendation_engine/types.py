from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from uuid import UUID


class AppealRecommendation(str, Enum):
    APPEAL_STRONGLY = "appeal_strongly"
    APPEAL = "appeal"
    MARGINAL = "marginal"
    DO_NOT_APPEAL = "do_not_appeal"
    INSUFFICIENT_DATA = "insufficient_data"


class AppealArgument(str, Enum):
    MARKET_VALUE = "market_value"
    UNIFORMITY = "uniformity"
    BOTH = "both"
    NONE = "none"


class CounterAppealRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class RecommendationConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class RecommendationResult:
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
    
    reasoning: tuple[str, ...] = field(default_factory=tuple)
    calculated_at: date | None = None