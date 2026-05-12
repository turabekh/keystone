import statistics
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.comp_engine.finder import CompCandidate, find_candidates
from app.services.comp_engine.scorer import score_candidate
from app.services.comp_engine.subject import SubjectFeatures, load_subject
from app.services.comp_engine.types import (
    CompUsed,
    ValuationConfidence,
    ValuationResult,
    CompSizeMatch,
)

from app.services.comp_engine.types import CompGeographicScope
from app.models.property import PropertyCategory


PHILLY_ANNUAL_APPRECIATION = 0.016
TOP_N_COMPS = 10
MIN_COMPS_HIGH_CONFIDENCE = 8
MIN_COMPS_MEDIUM_CONFIDENCE = 5
MIN_COMPS_LOW_CONFIDENCE = 3
MIN_PPSF_FLOOR_RESIDENTIAL = 50.0
IQR_OUTLIER_MULTIPLIER = 1.5


def _filter_outliers(
    ppsf_values: list[float],
    comps_used: list[CompUsed],
) -> tuple[list[float], list[CompUsed], int]:
    pairs = list(zip(ppsf_values, comps_used))
    
    # Absolute floor (distress sales)
    before = len(pairs)
    pairs = [(p, c) for p, c in pairs if p >= MIN_PPSF_FLOOR_RESIDENTIAL]
    floor_removed = before - len(pairs)
    
    if len(pairs) < 4:
        clean_ppsf = [p for p, _ in pairs]
        clean_comps = [c for _, c in pairs]
        return clean_ppsf, clean_comps, floor_removed
    
    # IQR-based filtering
    sorted_ppsf = sorted(p for p, _ in pairs)
    q1 = _percentile(sorted_ppsf, 0.25)
    q3 = _percentile(sorted_ppsf, 0.75)
    iqr = q3 - q1
    lower = q1 - IQR_OUTLIER_MULTIPLIER * iqr
    upper = q3 + IQR_OUTLIER_MULTIPLIER * iqr
    
    before = len(pairs)
    pairs = [(p, c) for p, c in pairs if lower <= p <= upper]
    iqr_removed = before - len(pairs)
    
    clean_ppsf = [p for p, _ in pairs]
    clean_comps = [c for _, c in pairs]
    return clean_ppsf, clean_comps, floor_removed + iqr_removed


def value_property(
    session: Session,
    property_id: UUID,
    *,
    as_of: date | None = None,
    annual_appreciation: float = PHILLY_ANNUAL_APPRECIATION,
) -> ValuationResult:
    as_of = as_of or date.today()

    subject = load_subject(session, property_id)

    if subject is not None and subject.property_category in {
        PropertyCategory.COMMERCIAL,
        PropertyCategory.MIXED_USE,
        PropertyCategory.OTHER,
    }:
        return ValuationResult(
            subject_property_id=property_id,
            point_estimate=None,
            low_estimate=None,
            high_estimate=None,
            confidence=ValuationConfidence.INSUFFICIENT_DATA,
            comp_count=0,
            notes=(
                f"Subject is a {subject.property_category.value} property; "
                f"comp-based valuation is not supported in v1. "
                f"Commercial and mixed-use appeals require manual appraisal.",
            ),
            calculated_at=as_of,
        )
    
    if subject is None:
        return ValuationResult(
            subject_property_id=property_id,
            point_estimate=None,
            low_estimate=None,
            high_estimate=None,
            confidence=ValuationConfidence.INSUFFICIENT_DATA,
            comp_count=0,
            notes=("Subject property not found",),
            calculated_at=as_of,
        )

    if subject.living_area is None or subject.living_area <= 0:
        return ValuationResult(
            subject_property_id=property_id,
            point_estimate=None,
            low_estimate=None,
            high_estimate=None,
            confidence=ValuationConfidence.INSUFFICIENT_DATA,
            comp_count=0,
            notes=("Subject property has no living area; cannot compute price per sqft",),
            calculated_at=as_of,
        )

    candidates = find_candidates(session, subject, as_of=as_of)
    scored = [
        (score_candidate(subject, c, as_of=as_of), c)
        for c in candidates
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:TOP_N_COMPS]

    if not top:
        return ValuationResult(
            subject_property_id=property_id,
            point_estimate=None,
            low_estimate=None,
            high_estimate=None,
            confidence=ValuationConfidence.INSUFFICIENT_DATA,
            comp_count=0,
            notes=("No arms-length comparable sales found within search radius",),
            calculated_at=as_of,
            time_adjustment_rate_annual=annual_appreciation,
        )

    comps_used: list[CompUsed] = []
    ppsf_values: list[float] = []
    for similarity, c in top:
        if c.living_area is None or c.living_area <= 0:
            continue
        months_ago = _months_between(c.sale_date, as_of)
        adjusted_price = _adjust_for_time(c.sale_price, months_ago, annual_appreciation)
        ppsf = adjusted_price / c.living_area
        ppsf_values.append(ppsf)
        comps_used.append(
            CompUsed(
                property_id=c.property_id,
                address_full=c.address_full,
                parcel_id=c.parcel_id,
                sale_date=c.sale_date,
                sale_price=c.sale_price,
                sale_price_adjusted=int(adjusted_price),
                living_area=c.living_area,
                price_per_sqft=round(ppsf, 2),
                similarity_score=round(similarity, 3),
                geographic_scope=c.geographic_scope,
                size_match=c.size_match,
                months_ago=months_ago,
            )
        )

    if not ppsf_values:
        return ValuationResult(
            subject_property_id=property_id,
            point_estimate=None,
            low_estimate=None,
            high_estimate=None,
            confidence=ValuationConfidence.INSUFFICIENT_DATA,
            comp_count=0,
            notes=("No comps had usable living area data for ppsf calculation",),
            calculated_at=as_of,
            time_adjustment_rate_annual=annual_appreciation,
        )
    
    ppsf_values, comps_used, outlier_count = _filter_outliers(ppsf_values, comps_used)

    if len(ppsf_values) < MIN_COMPS_LOW_CONFIDENCE:
        return ValuationResult(
            subject_property_id=property_id,
            point_estimate=None,
            low_estimate=None,
            high_estimate=None,
            confidence=ValuationConfidence.INSUFFICIENT_DATA,
            comp_count=len(ppsf_values),
            notes=(
                f"After removing {outlier_count} outliers, "
                f"only {len(ppsf_values)} comps remain (need at least {MIN_COMPS_LOW_CONFIDENCE})",
            ),
            calculated_at=as_of,
            time_adjustment_rate_annual=annual_appreciation,
        )

    # NEW: check for ward-level noise
    ward_comps = sum(1 for c in comps_used if c.geographic_scope == CompGeographicScope.SAME_WARD)
    ward_fraction = ward_comps / len(comps_used) if comps_used else 0.0
    if ward_fraction >= 0.5 and len(ppsf_values) >= 4:
        ppsf_range_ratio = max(ppsf_values) / min(ppsf_values) if min(ppsf_values) > 0 else 0
        if ppsf_range_ratio > 3.0:
            return ValuationResult(
                subject_property_id=property_id,
                point_estimate=None,
                low_estimate=None,
                high_estimate=None,
                confidence=ValuationConfidence.INSUFFICIENT_DATA,
                comp_count=len(ppsf_values),
                notes=(
                    f"Comp pool spans too much variance to produce a defensible estimate: "
                    f"price-per-sqft ranges from ${min(ppsf_values):.0f} to ${max(ppsf_values):.0f}. "
                    f"This typically means the only available comps are from a wide area with "
                    f"heterogeneous property values. Recommendation should be based on uniformity analysis only.",
                ),
                calculated_at=as_of,
                time_adjustment_rate_annual=annual_appreciation,
            )

    ppsf_sorted = sorted(ppsf_values)
    median_ppsf = statistics.median(ppsf_sorted)
    p25_ppsf = _percentile(ppsf_sorted, 0.25)
    p75_ppsf = _percentile(ppsf_sorted, 0.75)

    point = int(median_ppsf * subject.living_area)
    low = int(p25_ppsf * subject.living_area)
    high = int(p75_ppsf * subject.living_area)

    confidence = _classify_confidence(len(comps_used), comps_used)
    notes = _build_notes(comps_used, confidence, outlier_count)

    return ValuationResult(
        subject_property_id=property_id,
        point_estimate=point,
        low_estimate=low,
        high_estimate=high,
        confidence=confidence,
        comp_count=len(comps_used),
        comps=tuple(comps_used),
        notes=notes,
        time_adjustment_rate_annual=annual_appreciation,
        calculated_at=as_of,
    )


def _months_between(start: date, end: date) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


def _adjust_for_time(price: int, months_ago: int, annual_rate: float) -> float:
    return price * ((1 + annual_rate) ** (months_ago / 12))


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = p * (len(sorted_values) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def _classify_confidence(comp_count: int, comps: list[CompUsed]) -> ValuationConfidence:
    if comp_count < MIN_COMPS_LOW_CONFIDENCE:
        return ValuationConfidence.INSUFFICIENT_DATA
    
    same_block_count = sum(
        1 for c in comps if c.geographic_scope == CompGeographicScope.SAME_BLOCK
    )
    
    if comp_count >= MIN_COMPS_HIGH_CONFIDENCE and same_block_count >= 3:
        return ValuationConfidence.HIGH
    if comp_count >= MIN_COMPS_MEDIUM_CONFIDENCE:
        return ValuationConfidence.MEDIUM
    return ValuationConfidence.LOW


def _build_notes(comps: list[CompUsed], confidence: ValuationConfidence, outliers_removed: int = 0) -> tuple[str, ...]:
    notes: list[str] = []
    by_scope: dict[str, int] = {}
    for c in comps:
        by_scope[c.geographic_scope.value] = by_scope.get(c.geographic_scope.value, 0) + 1
    scope_parts = [f"{n} {scope.replace('_', ' ')}" for scope, n in by_scope.items()]
    notes.append("Comps drawn from: " + ", ".join(scope_parts))

    tight_count = sum(1 for c in comps if c.size_match == CompSizeMatch.TIGHT)
    loose_count = len(comps) - tight_count
    if comps:
        sizes = sorted(c.living_area for c in comps if c.living_area is not None)
        if sizes:
            notes.append(
                f"Comp size range: {sizes[0]:,}–{sizes[-1]:,} sqft "
                f"({tight_count} tight match, {loose_count} loose)"
            )

    if outliers_removed > 0:
        notes.append(
            f"Removed {outliers_removed} outlier sale(s) likely representing distress transactions"
        )

    if confidence == ValuationConfidence.LOW:
        notes.append("Confidence is low; consider this estimate a starting point only")
    elif confidence == ValuationConfidence.HIGH:
        notes.append("High confidence based on tight geographic and physical match")

    notes.append(
        "Estimate uses median price-per-sqft from comparable recorded sales. "
        "Actual market value may vary ±15% based on condition, school district, "
        "and other factors. For tax appeal purposes, this estimate reflects deed-recorded sales."
    )
    return tuple(notes)