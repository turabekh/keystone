from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.county import County


class CountyRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_by_state(self, state: str) -> Sequence[County]:
        stmt = (
            select(County)
            .where(County.state == state.upper())
            .order_by(County.name)
            .options(selectinload(County.year_settings))
        )
        return self.session.scalars(stmt).all()

    def get_by_state_and_slug(self, state: str, slug: str) -> County | None:
        stmt = (
            select(County)
            .where(County.state == state.upper(), County.slug == slug.lower())
            .options(selectinload(County.year_settings))
        )
        return self.session.scalars(stmt).one_or_none()