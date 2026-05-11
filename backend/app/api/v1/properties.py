from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.property import PropertyRepository
from app.schemas.property import PropertyDetail, PropertyLookupResult


router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("/lookup", response_model=list[PropertyLookupResult])
def lookup_properties(
    q: str = Query(..., min_length=3, description="Search query, partial address"),
    state: str = Query(..., min_length=2, max_length=2, description="2-letter state code"),
    county_slug: str = Query(..., description="County slug, e.g. 'philadelphia'"),
    limit: int = Query(10, ge=1, le=25),
    db: Session = Depends(get_db),
):
    repo = PropertyRepository(db)

    county_id = repo.get_county_id_by_state_and_slug(state, county_slug)
    if county_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"County not found: {state}/{county_slug}",
        )

    results = repo.lookup_by_address(query=q, county_id=county_id, limit=limit)

    return [
        PropertyLookupResult(
            id=prop.id,
            parcel_id=prop.parcel_id,
            address_full=prop.address_full,
            zip_code=prop.zip_code,
            property_category=prop.property_category,
            current_assessed_total=prop.current_assessed_total,
            similarity=float(score),
        )
        for prop, score in results
    ]


@router.get("/{property_id}", response_model=PropertyDetail)
def get_property(property_id: UUID, db: Session = Depends(get_db)):
    repo = PropertyRepository(db)
    prop = repo.get_by_id(property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop