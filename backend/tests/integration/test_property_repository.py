import pytest

from app.models.property import PropertyCategory
from app.repositories.property import PropertyRepository


@pytest.fixture
def philly_county_id(db_session):
    from sqlalchemy import select
    from app.models.county import County

    stmt = select(County).where(County.slug == "philadelphia", County.state == "PA")
    return db_session.scalars(stmt).one().id


@pytest.mark.integration
def test_lookup_returns_results_with_high_similarity(db_session, philly_county_id):
    repo = PropertyRepository(db_session)
    results = repo.lookup_by_address(query="overhill", county_id=philly_county_id, limit=10)
    assert len(results) > 0
    for prop, score in results:
        assert score >= 0.3


@pytest.mark.integration
def test_lookup_orders_by_similarity_desc(db_session, philly_county_id):
    repo = PropertyRepository(db_session)
    results = repo.lookup_by_address(query="market street", county_id=philly_county_id, limit=10)
    if len(results) >= 2:
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.integration
def test_lookup_respects_limit(db_session, philly_county_id):
    repo = PropertyRepository(db_session)
    results = repo.lookup_by_address(query="market", county_id=philly_county_id, limit=5)
    assert len(results) <= 5


@pytest.mark.integration
def test_lookup_empty_query_returns_empty(db_session, philly_county_id):
    repo = PropertyRepository(db_session)
    results = repo.lookup_by_address(query="   ", county_id=philly_county_id, limit=10)
    assert results == []


@pytest.mark.integration
def test_lookup_below_threshold_returns_empty(db_session, philly_county_id):
    repo = PropertyRepository(db_session)
    results = repo.lookup_by_address(
        query="xyzzyfrobnicatequuxbarbazxyzzy",
        county_id=philly_county_id,
        limit=10,
    )
    assert len(results) == 0


@pytest.mark.integration
def test_lookup_is_case_insensitive(db_session, philly_county_id):
    repo = PropertyRepository(db_session)
    lower = repo.lookup_by_address(query="overhill", county_id=philly_county_id, limit=5)
    upper = repo.lookup_by_address(query="OVERHILL", county_id=philly_county_id, limit=5)
    assert {p.id for p, _ in lower} == {p.id for p, _ in upper}


@pytest.mark.integration
def test_lookup_collapses_whitespace(db_session, philly_county_id):
    repo = PropertyRepository(db_session)
    normal = repo.lookup_by_address(query="market street", county_id=philly_county_id, limit=5)
    spaced = repo.lookup_by_address(query="market    street", county_id=philly_county_id, limit=5)
    assert {p.id for p, _ in normal} == {p.id for p, _ in spaced}


@pytest.mark.integration
def test_lookup_cap_enforced(db_session, philly_county_id):
    repo = PropertyRepository(db_session)
    results = repo.lookup_by_address(query="market", county_id=philly_county_id, limit=1000)
    assert len(results) <= 25


@pytest.mark.integration
def test_get_by_id_returns_property(db_session, philly_county_id):
    from sqlalchemy import select
    from app.models.property import Property

    stmt = select(Property).where(Property.county_id == philly_county_id).limit(1)
    existing = db_session.scalars(stmt).one()

    repo = PropertyRepository(db_session)
    found = repo.get_by_id(existing.id)
    assert found is not None
    assert found.id == existing.id
    assert found.parcel_id == existing.parcel_id


@pytest.mark.integration
def test_get_by_id_returns_none_for_missing(db_session):
    from uuid import uuid4
    repo = PropertyRepository(db_session)
    found = repo.get_by_id(uuid4())
    assert found is None


@pytest.mark.integration
def test_get_county_id_by_state_slug(db_session):
    repo = PropertyRepository(db_session)
    cid = repo.get_county_id_by_state_and_slug("PA", "philadelphia")
    assert cid is not None


@pytest.mark.integration
def test_get_county_id_case_insensitive(db_session):
    repo = PropertyRepository(db_session)
    cid_upper = repo.get_county_id_by_state_and_slug("pa", "PHILADELPHIA")
    cid_lower = repo.get_county_id_by_state_and_slug("PA", "philadelphia")
    assert cid_upper == cid_lower


@pytest.mark.integration
def test_get_county_id_missing_returns_none(db_session):
    repo = PropertyRepository(db_session)
    assert repo.get_county_id_by_state_and_slug("PA", "nonexistent") is None