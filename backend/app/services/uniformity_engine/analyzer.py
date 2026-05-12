import statistics
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.sale import Sale
from app.services.comp_engine import value_property
from app.services.comp_engine.subject import load_subject
from app.services.uniformity_engine.types import (
    BlockUniformityResult,
    NeighborhoodAsr,
    UniformityResult,
    UniformitySignal,
)


SUBJECT_SALE_MAX_AGE_MONTHS = 36
NEIGHBORHOOD_SALE_MAX_AGE_MONTHS = 18
MIN_NEIGHBORHOOD_SAMPLES = 8
MIN_BLOCK_SAMPLES = 5

STRONG_CASE_DEVIATION_THRESHOLD = 0.15
MODERATE_CASE_DEVIATION_THRESHOLD = 0.05


def analyze_uniformity(
    session: Session,
    property_id: UUID,
    *,
    as_of: date | None = None,
) -> UniformityResult:
    as_of = as_of or date.today()
    subject = load_subject(session, property_id)
    if subject is None:
        return UniformityResult(
            subject_property_id=property_id,
            subject_asr=None,
            subject_asr_source="unknown",
            neighborhood_median_asr=None,
            neighborhood_sample_size=0,
            block_result=None,
            deviation_from_neighborhood=None,
            deviation_from_block=None,
            signal=UniformitySignal.INSUFFICIENT_DATA,
            notes=("Subject property not found",),
            calculated_at=as_of,
        )

    subject_prop = session.get(Property, property_id)
    if subject_prop.current_assessed_total is None or subject_prop.current_assessed_total <= 0:
        return UniformityResult(
            subject_property_id=property_id,
            subject_asr=None,
            subject_asr_source="unknown",
            neighborhood_median_asr=None,
            neighborhood_sample_size=0,
            block_result=None,
            deviation_from_neighborhood=None,
            deviation_from_block=None,
            signal=UniformitySignal.INSUFFICIENT_DATA,
            notes=("Subject has no current assessment value",),
            calculated_at=as_of,
        )

    subject_assessment = subject_prop.current_assessed_total

    subject_market_value, subject_source = _resolve_subject_market_value(
        session, subject_prop, property_id, as_of
    )
    if subject_market_value is None:
        return UniformityResult(
            subject_property_id=property_id,
            subject_asr=None,
            subject_asr_source=subject_source,
            neighborhood_median_asr=None,
            neighborhood_sample_size=0,
            block_result=None,
            deviation_from_neighborhood=None,
            deviation_from_block=None,
            signal=UniformitySignal.INSUFFICIENT_DATA,
            notes=("Could not determine subject market value for uniformity analysis",),
            calculated_at=as_of,
        )

    subject_asr = subject_assessment / subject_market_value

    neighborhood_samples = _query_neighborhood_asrs(
        session,
        subject,
        as_of,
        scope_field="census_tract",
        scope_value=subject.census_tract,
    )
    
    block_result = None
    if subject.street_code and subject.hundred_block is not None:
        block_samples = _query_neighborhood_asrs(
            session,
            subject,
            as_of,
            scope_field="block",
            scope_value=(subject.street_code, subject.hundred_block),
        )
        if len(block_samples) >= MIN_BLOCK_SAMPLES:
            block_result = _build_block_result(
                subject.street_code,
                subject.hundred_block,
                block_samples,
            )

    if len(neighborhood_samples) < MIN_NEIGHBORHOOD_SAMPLES:
        return UniformityResult(
            subject_property_id=property_id,
            subject_asr=round(subject_asr, 4),
            subject_asr_source=subject_source,
            neighborhood_median_asr=None,
            neighborhood_sample_size=len(neighborhood_samples),
            block_result=block_result,
            deviation_from_neighborhood=None,
            deviation_from_block=None,
            signal=UniformitySignal.INSUFFICIENT_DATA,
            notes=(
                f"Only {len(neighborhood_samples)} recent neighborhood sales found "
                f"(need at least {MIN_NEIGHBORHOOD_SAMPLES})",
            ),
            calculated_at=as_of,
        )

    neighborhood_asrs = sorted(s.asr for s in neighborhood_samples)
    neighborhood_median = statistics.median(neighborhood_asrs)

    deviation_from_neighborhood = (subject_asr - neighborhood_median) / neighborhood_median
    deviation_from_block = None
    if block_result:
        deviation_from_block = (subject_asr - block_result.median_asr) / block_result.median_asr

    signal = _classify_signal(deviation_from_neighborhood, deviation_from_block)
    notes = _build_notes(
        subject_asr,
        subject_source,
        neighborhood_median,
        len(neighborhood_samples),
        block_result,
        deviation_from_neighborhood,
        deviation_from_block,
        signal,
    )

    return UniformityResult(
        subject_property_id=property_id,
        subject_asr=round(subject_asr, 4),
        subject_asr_source=subject_source,
        neighborhood_median_asr=round(neighborhood_median, 4),
        neighborhood_sample_size=len(neighborhood_samples),
        block_result=block_result,
        deviation_from_neighborhood=round(deviation_from_neighborhood, 4),
        deviation_from_block=round(deviation_from_block, 4) if deviation_from_block is not None else None,
        signal=signal,
        notes=notes,
        calculated_at=as_of,
    )


def _resolve_subject_market_value(
    session: Session,
    subject_prop: Property,
    property_id: UUID,
    as_of: date,
) -> tuple[int | None, str]:
    cutoff = date(as_of.year - 3, as_of.month, max(1, as_of.day))
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
    if recent_sale is not None and recent_sale.sale_price > 0:
        return recent_sale.sale_price, f"actual_sale_{recent_sale.sale_date.isoformat()}"

    valuation = value_property(session, property_id, as_of=as_of)
    if valuation.point_estimate is not None:
        return valuation.point_estimate, "comp_engine_estimate"

    return None, "unavailable"


def _query_neighborhood_asrs(
    session: Session,
    subject,
    as_of: date,
    *,
    scope_field: str,
    scope_value,
) -> list[NeighborhoodAsr]:
    cutoff = date(
        as_of.year - (NEIGHBORHOOD_SALE_MAX_AGE_MONTHS // 12),
        as_of.month,
        max(1, as_of.day),
    )
    
    if scope_field == "census_tract":
        scope_filter = Property.census_tract == scope_value
    elif scope_field == "block":
        street_code, hundred_block = scope_value
        scope_filter = (Property.street_code == street_code) & (Property.hundred_block == hundred_block)
    else:
        return []

    stmt = (
        select(
            Property.id,
            Property.address_full,
            Property.parcel_id,
            Property.current_assessed_total,
            Sale.sale_date,
            Sale.sale_price,
        )
        .join(Sale, Sale.property_id == Property.id)
        .where(
            Property.id != subject.property_id,
            Property.county_id == subject.county_id,
            Property.property_category == subject.property_category,
            scope_filter,
            Sale.is_arms_length.is_(True),
            Sale.sale_date >= cutoff,
            Sale.sale_price >= 10_000,
            Property.current_assessed_total.isnot(None),
            Property.current_assessed_total > 0,
        )
        .order_by(Sale.sale_date.desc())
        .limit(500)
    )

    rows = session.execute(stmt).all()
    samples: list[NeighborhoodAsr] = []
    for row in rows:
        asr = row.current_assessed_total / row.sale_price
        if 0.1 < asr < 5.0:
            samples.append(
                NeighborhoodAsr(
                    property_id=row.id,
                    address_full=row.address_full,
                    parcel_id=row.parcel_id,
                    sale_date=row.sale_date,
                    sale_price=row.sale_price,
                    assessment=row.current_assessed_total,
                    asr=asr,
                )
            )
    return samples


def _build_block_result(
    street_code: str,
    hundred_block: int,
    samples: list[NeighborhoodAsr],
) -> BlockUniformityResult:
    asrs = sorted(s.asr for s in samples)
    median = statistics.median(asrs)
    p25 = _percentile(asrs, 0.25)
    p75 = _percentile(asrs, 0.75)
    return BlockUniformityResult(
        block_id=f"{street_code}-{hundred_block}",
        median_asr=round(median, 4),
        sample_size=len(samples),
        asr_p25=round(p25, 4),
        asr_p75=round(p75, 4),
        samples=tuple(samples),
    )


def _classify_signal(
    deviation_from_neighborhood: float,
    deviation_from_block: float | None,
) -> UniformitySignal:
    # Use block deviation if available (more granular signal)
    primary_deviation = (
        deviation_from_block if deviation_from_block is not None else deviation_from_neighborhood
    )
    
    if primary_deviation > STRONG_CASE_DEVIATION_THRESHOLD:
        return UniformitySignal.STRONG_CASE
    if primary_deviation > MODERATE_CASE_DEVIATION_THRESHOLD:
        return UniformitySignal.MODERATE_CASE
    if primary_deviation > -MODERATE_CASE_DEVIATION_THRESHOLD:
        return UniformitySignal.NO_CASE
    return UniformitySignal.NO_CASE  # negative deviation = under-assessed = no appeal


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = p * (len(sorted_values) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def _build_notes(
    subject_asr: float,
    subject_source: str,
    neighborhood_median: float,
    neighborhood_sample_size: int,
    block_result: BlockUniformityResult | None,
    deviation_from_neighborhood: float,
    deviation_from_block: float | None,
    signal: UniformitySignal,
) -> tuple[str, ...]:
    notes: list[str] = []
    
    notes.append(
        f"Subject ASR: {subject_asr:.3f} (based on {subject_source})"
    )
    notes.append(
        f"Neighborhood median ASR: {neighborhood_median:.3f} "
        f"(from {neighborhood_sample_size} recent arms-length sales)"
    )
    
    if block_result:
        notes.append(
            f"Block median ASR: {block_result.median_asr:.3f} "
            f"(from {block_result.sample_size} sales on same hundred-block)"
        )
    
    if deviation_from_neighborhood > 0:
        notes.append(
            f"Subject is over-assessed by {deviation_from_neighborhood:.1%} "
            f"vs. neighborhood median"
        )
    else:
        notes.append(
            f"Subject is under-assessed by {abs(deviation_from_neighborhood):.1%} "
            f"vs. neighborhood median"
        )
    
    if signal == UniformitySignal.STRONG_CASE:
        notes.append(
            "STRONG uniformity case: assessment deviation exceeds 15% — "
            "Pennsylvania law requires uniform assessment; this is appealable"
        )
    elif signal == UniformitySignal.MODERATE_CASE:
        notes.append(
            "Moderate uniformity case: deviation in the 5-15% range; "
            "appeal may succeed but evidence should be carefully presented"
        )
    elif signal == UniformitySignal.NO_CASE:
        notes.append(
            "No uniformity case: assessment is consistent with neighborhood norms"
        )
    
    return tuple(notes)