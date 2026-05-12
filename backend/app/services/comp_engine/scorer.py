from datetime import date
from typing import Final

from app.services.comp_engine.finder import CompCandidate
from app.services.comp_engine.subject import SubjectFeatures
from app.services.comp_engine.types import CompGeographicScope


_SCOPE_WEIGHT: Final[dict[CompGeographicScope, float]] = {
    CompGeographicScope.SAME_BLOCK: 1.0,
    CompGeographicScope.SAME_CENSUS_TRACT: 0.75,
    CompGeographicScope.SAME_WARD: 0.50,
}


def score_candidate(
    subject: SubjectFeatures,
    candidate: CompCandidate,
    *,
    as_of: date,
) -> float:
    geo = _SCOPE_WEIGHT[candidate.geographic_scope]
    
    living = _proximity_score(subject.living_area, candidate.living_area, tolerance_pct=0.15)
    lot = _proximity_score(subject.lot_area, candidate.lot_area, tolerance_pct=0.40)
    age = _age_score(subject.year_built, candidate.year_built, tolerance_years=20)
    beds = _exact_score_with_tolerance(subject.bedrooms, candidate.bedrooms, tolerance=1)
    baths = _exact_score_with_tolerance(
        subject.bathrooms,
        candidate.bathrooms,
        tolerance=1.0,
    )
    recency = _recency_score(candidate.sale_date, as_of, half_life_months=18)
    
    physical = (
        0.50 * living
        + 0.05 * lot
        + 0.10 * age
        + 0.10 * beds
        + 0.10 * baths
        + 0.15 * recency
    )
    
    return geo * physical

def _proximity_score(subject_val: int | None, candidate_val: int | None, *, tolerance_pct: float) -> float:
    if subject_val is None or candidate_val is None:
        return 0.5
    if subject_val == 0:
        return 0.5
    diff_pct = abs(subject_val - candidate_val) / subject_val
    if diff_pct <= tolerance_pct:
        return 1.0 - (diff_pct / tolerance_pct) * 0.5
    return max(0.0, 0.5 - (diff_pct - tolerance_pct))


def _age_score(subject_year: int | None, candidate_year: int | None, *, tolerance_years: int) -> float:
    if subject_year is None or candidate_year is None:
        return 0.5
    diff = abs(subject_year - candidate_year)
    if diff <= tolerance_years:
        return 1.0 - (diff / tolerance_years) * 0.5
    return max(0.0, 0.5 - (diff - tolerance_years) * 0.02)


def _exact_score_with_tolerance(subject_val: int | float | None, candidate_val: int | float | None, *, tolerance: float) -> float:
    if subject_val is None or candidate_val is None:
        return 0.5
    diff = abs(subject_val - candidate_val)
    if diff == 0:
        return 1.0
    if diff <= tolerance:
        return 0.7
    return max(0.0, 0.7 - (diff - tolerance) * 0.2)


def _recency_score(sale_date: date, as_of: date, *, half_life_months: int) -> float:
    months_ago = max(0, (as_of.year - sale_date.year) * 12 + (as_of.month - sale_date.month))
    return 0.5 ** (months_ago / half_life_months)