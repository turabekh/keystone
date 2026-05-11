from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.county import CountyRepository
from app.schemas.county import CountyWithSettings


router = APIRouter(prefix="/counties", tags=["counties"])


@router.get("/", response_model=list[CountyWithSettings])
def list_counties(state: str = "PA", db: Session = Depends(get_db)):
    repo = CountyRepository(db)
    return repo.list_by_state(state)


@router.get("/{state}/{slug}", response_model=CountyWithSettings)
def get_county(state: str, slug: str, db: Session = Depends(get_db)):
    repo = CountyRepository(db)
    county = repo.get_by_state_and_slug(state, slug)
    if county is None:
        raise HTTPException(status_code=404, detail="County not found")
    return county