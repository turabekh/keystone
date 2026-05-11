import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.property import Property, PropertyCategory
from app.models.sale import Sale
from app.services.comp_engine.subject import SubjectFeatures
from app.services.comp_engine.types import CompGeographicScope


logger = logging.getLogger(__name__)

MAX_MONTHS_BACK = 24
MIN_COMPS_FOR_TIGHT_SCOPE = 8
MAX_CANDIDATES = 200


@dataclass(frozen=True, slots=True)
class CompCandidate:
    property_id: UUID
    parcel_id: str
    address_full: str
    property_category: PropertyCategory
    census_tract: str | None
    geographic_ward: str | None
    street_code: str | None
    hundred_block: int | None
    living_area: int | None
    lot_area: int | None
    year_built: int | None
    bedrooms: int | None
    bathrooms: float | None
    sale_id: UUID
    sale_date: date
    sale_price: int
    geographic_scope: CompGeographicScope


def find_candidates(
    session: Session,
    subject: SubjectFeatures,
    *,
    as_of: date,
    max_months_back: int = MAX_MONTHS_BACK,
) -> list[CompCandidate]:
    earliest_sale_date = _date_n_months_before(as_of, max_months_back)

    candidates = _query_at_scope(
        session,
        subject,
        earliest_sale_date,
        CompGeographicScope.SAME_BLOCK,
    )
    if len(candidates) >= MIN_COMPS_FOR_TIGHT_SCOPE:
        return candidates

    tract_candidates = _query_at_scope(
        session,
        subject,
        earliest_sale_date,
        CompGeographicScope.SAME_CENSUS_TRACT,
    )
    seen = {c.property_id for c in candidates}
    candidates.extend(c for c in tract_candidates if c.property_id not in seen)
    if len(candidates) >= MIN_COMPS_FOR_TIGHT_SCOPE:
        return candidates

    ward_candidates = _query_at_scope(
        session,
        subject,
        earliest_sale_date,
        CompGeographicScope.SAME_WARD,
    )
    seen = {c.property_id for c in candidates}
    candidates.extend(c for c in ward_candidates if c.property_id not in seen)
    return candidates


def _query_at_scope(
    session: Session,
    subject: SubjectFeatures,
    earliest_sale_date: date,
    scope: CompGeographicScope,
) -> list[CompCandidate]:
    geo_filter = _geographic_filter(subject, scope)
    if geo_filter is None:
        return []

    stmt = (
        select(
            Property.id,
            Property.parcel_id,
            Property.address_full,
            Property.property_category,
            Property.census_tract,
            Property.geographic_ward,
            Property.street_code,
            Property.hundred_block,
            Property.square_feet_living,
            Property.square_feet_lot,
            Property.year_built,
            Property.number_of_bedrooms,
            Property.number_of_bathrooms,
            Sale.id.label("sale_id"),
            Sale.sale_date,
            Sale.sale_price,
        )
        .join(Sale, Sale.property_id == Property.id)
        .where(
            Property.id != subject.property_id,
            Property.county_id == subject.county_id,
            Property.property_category == subject.property_category,
            Sale.is_arms_length.is_(True),
            Sale.sale_date >= earliest_sale_date,
            geo_filter,
        )
        .order_by(Sale.sale_date.desc())
        .limit(MAX_CANDIDATES)
    )

    rows = session.execute(stmt).all()
    return [
        CompCandidate(
            property_id=row.id,
            parcel_id=row.parcel_id,
            address_full=row.address_full,
            property_category=row.property_category,
            census_tract=row.census_tract,
            geographic_ward=row.geographic_ward,
            street_code=row.street_code,
            hundred_block=row.hundred_block,
            living_area=row.square_feet_living,
            lot_area=row.square_feet_lot,
            year_built=row.year_built,
            bedrooms=row.number_of_bedrooms,
            bathrooms=float(row.number_of_bathrooms) if row.number_of_bathrooms else None,
            sale_id=row.sale_id,
            sale_date=row.sale_date,
            sale_price=row.sale_price,
            geographic_scope=scope,
        )
        for row in rows
    ]


def _geographic_filter(subject: SubjectFeatures, scope: CompGeographicScope):
    if scope == CompGeographicScope.SAME_BLOCK:
        if not subject.street_code or subject.hundred_block is None:
            return None
        return and_(
            Property.street_code == subject.street_code,
            Property.hundred_block == subject.hundred_block,
        )
    if scope == CompGeographicScope.SAME_CENSUS_TRACT:
        if not subject.census_tract:
            return None
        return Property.census_tract == subject.census_tract
    if scope == CompGeographicScope.SAME_WARD:
        if not subject.geographic_ward:
            return None
        return Property.geographic_ward == subject.geographic_ward
    return None


def _date_n_months_before(d: date, months: int) -> date:
    year = d.year
    month = d.month - months
    while month <= 0:
        month += 12
        year -= 1
    try:
        return date(year, month, d.day)
    except ValueError:
        return date(year, month, 28)