from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.county import County
from app.models.property import Property


MIN_SIMILARITY = 0.3
MAX_LIMIT = 25


class PropertyRepository:
    def __init__(self, session: Session):
        self.session = session

    def lookup_by_address(
        self,
        *,
        query: str,
        county_id: UUID,
        limit: int = 10,
    ) -> Sequence[tuple[Property, float]]:
        normalized = " ".join(query.lower().split())
        if not normalized:
            return []

        limit = min(max(1, limit), MAX_LIMIT)

        similarity = func.similarity(Property.address_normalized, normalized).label("similarity")

        stmt = (
            select(Property, similarity)
            .where(
                Property.county_id == county_id,
                func.similarity(Property.address_normalized, normalized) >= MIN_SIMILARITY,
            )
            .order_by(similarity.desc(), Property.address_full, Property.id)
            .limit(limit)
        )

        return list(self.session.execute(stmt).all())

    def get_by_id(self, property_id: UUID) -> Property | None:
        stmt = (
            select(Property)
            .where(Property.id == property_id)
            .options(selectinload(Property.sales))
        )
        return self.session.scalars(stmt).one_or_none()

    def get_county_id_by_state_and_slug(self, state: str, slug: str) -> UUID | None:
        stmt = (
            select(County.id)
            .where(County.state == state.upper(), County.slug == slug.lower())
        )
        return self.session.scalars(stmt).one_or_none()