from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.county import CountyYearSetting
from app.models.property import Property, PropertyCategory
from app.models.sale import Sale
from app.services.comp_engine import value_property
from app.services.comp_engine.types import ValuationConfidence
from app.services.recommendation_engine.types import (
    AppealArgument,
    AppealRecommendation,
    CounterAppealRisk,
    RecommendationConfidence,
    RecommendationResult,
)
from app.services.uniformity_engine import analyze_uniformity
from app.services.uniformity_engine.types import UniformitySignal


COUNTER_APPEAL_MEDIUM_RATIO = 1.20
COUNTER_APPEAL_HIGH_RATIO = 1.30
COUNTER_APPEAL_RECENT_SALE_MONTHS = 36
MIN_MEANINGFUL_ANNUAL_SAVINGS = 250
DEFAULT_TAX_YEAR = 2027


def recommend_appeal(
    session: Session,
    property_id: UUID,
    *,
    as_of: date | None = None,
    tax_year: int = DEFAULT_TAX_YEAR,
) -> RecommendationResult:
    as_of = as_of or date.today()
    
    subject = session.get(Property, property_id)
    if subject is None:
        return _insufficient(property_id, as_of, current_assessment=0, reason="Subject property not found")
    
    current_assessment = subject.current_assessed_total or 0
    if current_assessment <= 0:
        return _insufficient(
            property_id, as_of,
            current_assessment=0,
            reason="Subject property has no current assessment",
        )
    
    effective_tax_rate = _get_effective_tax_rate(session, subject.county_id, tax_year)
    if effective_tax_rate is None:
        return _insufficient(
            property_id, as_of,
            current_assessment=current_assessment,
            reason=f"No effective tax rate configured for tax_year {tax_year}",
        )
    
    valuation = value_property(session, property_id, as_of=as_of)
    uniformity = analyze_uniformity(session, property_id, as_of=as_of)
    
    market_value_estimate = valuation.point_estimate
    market_value_target = _market_value_appeal_target(valuation)
    uniformity_target = _uniformity_appeal_target(current_assessment, uniformity)
    
    candidate_targets = [t for t in (market_value_target, uniformity_target) if t is not None]
    if not candidate_targets:
        return _insufficient(
            property_id, as_of,
            current_assessment=current_assessment,
            reason="Neither comp engine nor uniformity engine produced a usable appeal target",
        )
    
    appeal_target = min(candidate_targets)

    if (
        market_value_target is not None
        and uniformity_target is not None
        and market_value_target < uniformity_target * 0.7
    ):
        # Market-value target is much lower than uniformity target — likely a comp engine miss
        # Use uniformity target instead and lower confidence
        appeal_target = uniformity_target
    
    if appeal_target >= current_assessment:
        primary_argument = AppealArgument.NONE
        recommendation = AppealRecommendation.DO_NOT_APPEAL
        reasoning = _build_no_case_reasoning(valuation, uniformity, current_assessment, market_value_estimate)
        return RecommendationResult(
            subject_property_id=property_id,
            recommendation=recommendation,
            primary_argument=primary_argument,
            confidence=RecommendationConfidence.HIGH,
            current_assessment=current_assessment,
            market_value_estimate=market_value_estimate,
            appeal_target_assessment=appeal_target,
            annual_tax_savings=0,
            three_year_savings=0,
            counter_appeal_risk=CounterAppealRisk.LOW,
            reasoning=reasoning,
            calculated_at=as_of,
        )
    
    annual_savings = int((current_assessment - appeal_target) * effective_tax_rate)
    three_year_savings = annual_savings * 3
    
    primary_argument = _classify_argument(
        market_value_target,
        uniformity_target,
        appeal_target,
    )
    
    counter_appeal_risk = _assess_counter_appeal_risk(
        session, property_id, current_assessment, appeal_target, as_of,
        subject_category=subject.property_category,
        valuation=valuation,
    )
    
    recommendation = _classify_recommendation(
        valuation_confidence=valuation.confidence,
        uniformity_signal=uniformity.signal,
        primary_argument=primary_argument,
        annual_savings=annual_savings,
        counter_appeal_risk=counter_appeal_risk,
    )
    
    confidence = _classify_recommendation_confidence(
        valuation.confidence, uniformity.signal, primary_argument,
    )

    if recommendation == AppealRecommendation.DO_NOT_APPEAL:
        annual_savings = 0
        three_year_savings = 0
    
    reasoning = _build_reasoning(
        valuation,
        uniformity,
        current_assessment,
        appeal_target,
        annual_savings,
        primary_argument,
        counter_appeal_risk,
        recommendation,
    )
    
    return RecommendationResult(
        subject_property_id=property_id,
        recommendation=recommendation,
        primary_argument=primary_argument,
        confidence=confidence,
        current_assessment=current_assessment,
        market_value_estimate=market_value_estimate,
        appeal_target_assessment=appeal_target,
        annual_tax_savings=annual_savings,
        three_year_savings=three_year_savings,
        counter_appeal_risk=counter_appeal_risk,
        reasoning=reasoning,
        calculated_at=as_of,
    )


def _get_effective_tax_rate(session: Session, county_id: UUID, tax_year: int) -> float | None:
    stmt = (
        select(CountyYearSetting)
        .where(
            CountyYearSetting.county_id == county_id,
            CountyYearSetting.tax_year == tax_year,
        )
    )
    setting = session.scalars(stmt).one_or_none()
    if setting is None or setting.effective_tax_rate is None:
        return None
    return float(setting.effective_tax_rate)


def _market_value_appeal_target(valuation) -> int | None:
    if valuation.point_estimate is None or valuation.point_estimate <= 0:
        return None
    if valuation.confidence not in {ValuationConfidence.HIGH, ValuationConfidence.MEDIUM}:
        return None
    # Use the comp engine's point estimate as appeal target. Don't go below low_estimate
    # because that's outside our confidence range.
    return valuation.point_estimate


def _uniformity_appeal_target(current_assessment: int, uniformity) -> int | None:
    if uniformity.signal == UniformitySignal.INSUFFICIENT_DATA:
        return None
    if uniformity.subject_asr is None or uniformity.neighborhood_median_asr is None:
        return None
    if uniformity.subject_asr <= uniformity.neighborhood_median_asr:
        return None  # Subject is already at or below neighborhood norm
    # Argue: reduce assessment so subject ASR matches neighborhood median ASR
    # new_assessment = current_assessment * (neighborhood_median_asr / subject_asr)
    ratio = uniformity.neighborhood_median_asr / uniformity.subject_asr
    return int(current_assessment * ratio)


def _classify_argument(
    market_target: int | None,
    uniformity_target: int | None,
    final_target: int,
) -> AppealArgument:
    market_supports = market_target is not None and market_target == final_target
    uniformity_supports = uniformity_target is not None and uniformity_target == final_target
    
    both_within_5_pct = (
        market_target is not None
        and uniformity_target is not None
        and abs(market_target - uniformity_target) / max(market_target, uniformity_target) < 0.05
    )
    
    if both_within_5_pct:
        return AppealArgument.BOTH
    if market_supports:
        return AppealArgument.MARKET_VALUE
    if uniformity_supports:
        return AppealArgument.UNIFORMITY
    return AppealArgument.NONE


def _assess_counter_appeal_risk(
    session: Session,
    property_id: UUID,
    current_assessment: int,
    appeal_target: int,
    as_of: date,
    subject_category: PropertyCategory | None = None,
    valuation = None,
) -> CounterAppealRisk:
    # First check: subject's own recent sale anchors our market reality.
    cutoff = date(
        as_of.year - (COUNTER_APPEAL_RECENT_SALE_MONTHS // 12),
        as_of.month,
        max(1, as_of.day),
    )
    stmt = (
        select(Sale)
        .where(
            Sale.property_id == property_id,
            Sale.is_arms_length.is_(True),
            Sale.sale_date >= cutoff,
        )
        .order_by(Sale.sale_date.desc())
        .limit(1)
    )
    recent_sale = session.scalars(stmt).first()
    if recent_sale is not None:
        if recent_sale.sale_price >= appeal_target * COUNTER_APPEAL_HIGH_RATIO:
            return CounterAppealRisk.HIGH
        if recent_sale.sale_price >= appeal_target * COUNTER_APPEAL_MEDIUM_RATIO:
            return CounterAppealRisk.MEDIUM
        return CounterAppealRisk.LOW

    # Second check: no recent sale to anchor market reality.
    # If we're proposing a >40% assessment reduction, require HIGH-confidence
    # comp evidence to trust the appeal target. Otherwise default to HIGH risk.
    large_reduction = (
        current_assessment > 0
        and appeal_target < current_assessment * 0.6
    )
    if large_reduction:
        comp_confidence_is_high = (
            valuation is not None
            and valuation.confidence == ValuationConfidence.HIGH
        )
        if not comp_confidence_is_high:
            return CounterAppealRisk.HIGH

    return CounterAppealRisk.LOW


def _classify_recommendation(
    *,
    valuation_confidence: ValuationConfidence,
    uniformity_signal: UniformitySignal,
    primary_argument: AppealArgument,
    annual_savings: int,
    counter_appeal_risk: CounterAppealRisk,
) -> AppealRecommendation:
    if annual_savings < MIN_MEANINGFUL_ANNUAL_SAVINGS:
        return AppealRecommendation.DO_NOT_APPEAL
    
    if counter_appeal_risk == CounterAppealRisk.HIGH:
        return AppealRecommendation.DO_NOT_APPEAL
    
    if primary_argument == AppealArgument.NONE:
        return AppealRecommendation.DO_NOT_APPEAL
    
    strong_uniformity = uniformity_signal == UniformitySignal.STRONG_CASE
    moderate_uniformity = uniformity_signal == UniformitySignal.MODERATE_CASE
    valuation_solid = valuation_confidence in {ValuationConfidence.HIGH, ValuationConfidence.MEDIUM}
    
    if primary_argument == AppealArgument.BOTH and strong_uniformity and valuation_solid:
        return AppealRecommendation.APPEAL_STRONGLY
    
    if strong_uniformity and counter_appeal_risk == CounterAppealRisk.LOW:
        return AppealRecommendation.APPEAL_STRONGLY
    
    if (moderate_uniformity or primary_argument == AppealArgument.MARKET_VALUE) and valuation_solid:
        if counter_appeal_risk == CounterAppealRisk.MEDIUM:
            return AppealRecommendation.MARGINAL
        return AppealRecommendation.APPEAL
    
    return AppealRecommendation.MARGINAL


def _classify_recommendation_confidence(
    valuation_confidence: ValuationConfidence,
    uniformity_signal: UniformitySignal,
    primary_argument: AppealArgument,
) -> RecommendationConfidence:
    if primary_argument == AppealArgument.BOTH:
        return RecommendationConfidence.HIGH
    if uniformity_signal == UniformitySignal.STRONG_CASE:
        return RecommendationConfidence.HIGH
    if valuation_confidence == ValuationConfidence.HIGH:
        return RecommendationConfidence.HIGH
    if (
        uniformity_signal == UniformitySignal.MODERATE_CASE
        or valuation_confidence == ValuationConfidence.MEDIUM
    ):
        return RecommendationConfidence.MEDIUM
    return RecommendationConfidence.LOW


def _build_reasoning(
    valuation,
    uniformity,
    current_assessment: int,
    appeal_target: int,
    annual_savings: int,
    primary_argument: AppealArgument,
    counter_appeal_risk: CounterAppealRisk,
    recommendation: AppealRecommendation,
) -> tuple[str, ...]:
    reasoning: list[str] = []
    
    reasoning.append(
        f"Current assessment: ${current_assessment:,}"
    )
    if valuation.point_estimate:
        reasoning.append(
            f"Estimated market value (comp engine): ${valuation.point_estimate:,} "
            f"({valuation.confidence.value} confidence, {valuation.comp_count} comps)"
        )
    if uniformity.subject_asr is not None:
        reasoning.append(
            f"Subject assessment-to-sale ratio (ASR): {uniformity.subject_asr:.2f}"
        )
        if uniformity.neighborhood_median_asr is not None:
            reasoning.append(
                f"Neighborhood median ASR: {uniformity.neighborhood_median_asr:.2f} "
                f"({uniformity.neighborhood_sample_size} sales)"
            )
            if uniformity.deviation_from_neighborhood is not None and uniformity.deviation_from_neighborhood > 0:
                reasoning.append(
                    f"Subject is {uniformity.deviation_from_neighborhood:.0%} over-assessed "
                    f"vs. neighborhood norm"
                )
    
    reasoning.append(f"Appeal target assessment: ${appeal_target:,}")
    reasoning.append(f"Annual tax savings if successful: ${annual_savings:,}")
    
    if primary_argument == AppealArgument.MARKET_VALUE:
        reasoning.append("Primary argument: MARKET VALUE — assessment exceeds comparable sales")
    elif primary_argument == AppealArgument.UNIFORMITY:
        reasoning.append(
            "Primary argument: UNIFORMITY — assessment is harsh relative to neighbors "
            "(PA Constitution Art. VIII §1)"
        )
    elif primary_argument == AppealArgument.BOTH:
        reasoning.append(
            "Primary arguments: BOTH market value and uniformity support a reduction; "
            "use both at appeal for strongest case"
        )
    
    if counter_appeal_risk == CounterAppealRisk.HIGH:
        reasoning.append(
            "HIGH counter-appeal risk: appeal target is significantly below current assessment, "
            "and we lack high-confidence evidence (either a recent subject sale or strong same-block comps) "
            "to defend that target. School district may successfully counter-appeal upward. Not recommended."
        )
    elif counter_appeal_risk == CounterAppealRisk.MEDIUM:
        reasoning.append(
            "MEDIUM counter-appeal risk: recent sale price is moderately above proposed target. "
            "Proceed with caution; expect school district resistance."
        )
    
    if recommendation == AppealRecommendation.APPEAL_STRONGLY:
        reasoning.append(
            "Recommendation: APPEAL STRONGLY — multiple strong signals, low counter-appeal risk"
        )
    elif recommendation == AppealRecommendation.APPEAL:
        reasoning.append(
            "Recommendation: APPEAL — meaningful savings, defensible argument"
        )
    elif recommendation == AppealRecommendation.MARGINAL:
        reasoning.append(
            "Recommendation: MARGINAL — savings possible but uncertain; weigh effort vs reward"
        )
    elif recommendation == AppealRecommendation.DO_NOT_APPEAL:
        reasoning.append(
            "Recommendation: DO NOT APPEAL — no defensible reduction, or risk exceeds benefit"
        )
    
    return tuple(reasoning)


def _build_no_case_reasoning(
    valuation,
    uniformity,
    current_assessment: int,
    market_value_estimate: int | None,
) -> tuple[str, ...]:
    reasoning: list[str] = []
    reasoning.append(f"Current assessment: ${current_assessment:,}")
    if market_value_estimate:
        reasoning.append(
            f"Estimated market value: ${market_value_estimate:,} "
            f"(below current assessment, so no market-value argument)"
        )
    if uniformity.subject_asr is not None and uniformity.neighborhood_median_asr is not None:
        if uniformity.subject_asr <= uniformity.neighborhood_median_asr:
            reasoning.append(
                f"Subject ASR {uniformity.subject_asr:.2f} is at or below "
                f"neighborhood median {uniformity.neighborhood_median_asr:.2f} — "
                f"no uniformity argument"
            )
    reasoning.append("Recommendation: DO NOT APPEAL — you are not over-assessed")
    return tuple(reasoning)


def _insufficient(
    property_id: UUID,
    as_of: date,
    current_assessment: int,
    reason: str,
) -> RecommendationResult:
    return RecommendationResult(
        subject_property_id=property_id,
        recommendation=AppealRecommendation.INSUFFICIENT_DATA,
        primary_argument=AppealArgument.NONE,
        confidence=RecommendationConfidence.LOW,
        current_assessment=current_assessment,
        market_value_estimate=None,
        appeal_target_assessment=None,
        annual_tax_savings=None,
        three_year_savings=None,
        counter_appeal_risk=CounterAppealRisk.UNKNOWN,
        reasoning=(reason,),
        calculated_at=as_of,
    )