from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.property import Property, PropertyCategory


@dataclass(frozen=True, slots=True)
class SubjectFeatures:
    property_id: UUID
    parcel_id: str
    address_full: str
    county_id: UUID
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


def load_subject(session: Session, property_id: UUID) -> SubjectFeatures | None:
    prop = session.get(Property, property_id)
    if prop is None:
        return None
    return SubjectFeatures(
        property_id=prop.id,
        parcel_id=prop.parcel_id,
        address_full=prop.address_full,
        county_id=prop.county_id,
        property_category=prop.property_category,
        census_tract=prop.census_tract,
        geographic_ward=prop.geographic_ward,
        street_code=prop.street_code,
        hundred_block=prop.hundred_block,
        living_area=prop.square_feet_living,
        lot_area=prop.square_feet_lot,
        year_built=prop.year_built,
        bedrooms=prop.number_of_bedrooms,
        bathrooms=float(prop.number_of_bathrooms) if prop.number_of_bathrooms else None,
    )