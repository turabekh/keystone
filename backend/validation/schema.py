from dataclasses import dataclass, field
from typing import Literal


AppealRecommendation = Literal[
    "appeal_strongly",
    "appeal",
    "marginal",
    "do_not_appeal",
    "insufficient_data",
]

AppealArgument = Literal["market_value", "uniformity", "both", "none"]
CounterAppealRisk = Literal["low", "medium", "high", "unknown"]
ValuationConfidence = Literal["high", "medium", "low", "insufficient_data"]


@dataclass(frozen=True, slots=True)
class ExpectedCase:
    """Human-judged expected outcome for a validation property.
    
    Fields that are None mean 'no assertion' — the engine output isn't checked
    against these fields.
    """
    test_id: str
    address_query: str
    state: str = "PA"
    county_slug: str = "philadelphia"
    
    # Property identification (used to verify lookup found the right property)
    expected_parcel_id: str | None = None
    expected_address_contains: str | None = None
    
    # Recommendation expectations
    expected_recommendation: AppealRecommendation | None = None
    expected_argument: AppealArgument | None = None
    expected_counter_appeal_risk: CounterAppealRisk | None = None
    
    # Numeric ranges (inclusive)
    expected_annual_savings_min: int | None = None
    expected_annual_savings_max: int | None = None
    
    # Comp engine expectations
    expected_valuation_confidence: ValuationConfidence | None = None
    expected_point_estimate_min: int | None = None
    expected_point_estimate_max: int | None = None
    expected_comp_count_min: int | None = None
    
    # Uniformity expectations
    expected_uniformity_signal: Literal[
        "strong_case", "moderate_case", "weak_case", "no_case", "insufficient_data",
    ] | None = None
    
    # Free-form notes about why this case was chosen
    notes: str = ""
    
    # Optional: tag categorizing the case
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class ValidationOutcome:
    """Result of running one expected case against the engine."""
    case: ExpectedCase
    passed: bool
    property_id: str | None
    failures: list[str] = field(default_factory=list)