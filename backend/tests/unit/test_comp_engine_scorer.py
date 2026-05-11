from datetime import date
from uuid import uuid4

from app.models.property import PropertyCategory
from app.services.comp_engine.finder import CompCandidate
from app.services.comp_engine.scorer import score_candidate
from app.services.comp_engine.subject import SubjectFeatures
from app.services.comp_engine.types import CompGeographicScope


def _subject(**overrides) -> SubjectFeatures:
    base = dict(
        property_id=uuid4(),
        parcel_id="P-SUBJECT",
        address_full="1204 MASTER ST",
        county_id=uuid4(),
        property_category=PropertyCategory.ROWHOUSE,
        census_tract="146",
        geographic_ward="14",
        street_code="54280",
        hundred_block=1200,
        living_area=1360,
        lot_area=1760,
        year_built=1960,
        bedrooms=3,
        bathrooms=1.0,
    )
    base.update(overrides)
    return SubjectFeatures(**base)


def _candidate(**overrides) -> CompCandidate:
    base = dict(
        property_id=uuid4(),
        parcel_id="P-COMP",
        address_full="1215 MASTER ST",
        property_category=PropertyCategory.ROWHOUSE,
        census_tract="146",
        geographic_ward="14",
        street_code="54280",
        hundred_block=1200,
        living_area=1340,
        lot_area=1700,
        year_built=1962,
        bedrooms=3,
        bathrooms=1.0,
        sale_id=uuid4(),
        sale_date=date(2025, 6, 1),
        sale_price=290000,
        geographic_scope=CompGeographicScope.SAME_BLOCK,
    )
    base.update(overrides)
    return CompCandidate(**base)


def test_perfect_block_match_scores_very_high():
    s = _subject()
    c = _candidate()
    score = score_candidate(s, c, as_of=date(2026, 5, 1))
    assert score >= 0.75


def test_same_block_beats_same_tract_when_identical():
    s = _subject()
    block_comp = _candidate()
    tract_comp = _candidate(
        geographic_scope=CompGeographicScope.SAME_CENSUS_TRACT,
        hundred_block=2400,
    )
    block_score = score_candidate(s, block_comp, as_of=date(2026, 5, 1))
    tract_score = score_candidate(s, tract_comp, as_of=date(2026, 5, 1))
    assert block_score > tract_score


def test_old_sale_scores_lower_than_recent():
    s = _subject()
    recent = _candidate(sale_date=date(2026, 3, 1))
    old = _candidate(sale_date=date(2024, 1, 1))
    recent_score = score_candidate(s, recent, as_of=date(2026, 5, 1))
    old_score = score_candidate(s, old, as_of=date(2026, 5, 1))
    assert recent_score > old_score


def test_living_area_mismatch_drops_score():
    s = _subject(living_area=1360)
    similar = _candidate(living_area=1340)
    different = _candidate(living_area=2800)
    similar_score = score_candidate(s, similar, as_of=date(2026, 5, 1))
    different_score = score_candidate(s, different, as_of=date(2026, 5, 1))
    assert similar_score > different_score


def test_missing_living_area_uses_neutral_score():
    s = _subject()
    no_data = _candidate(living_area=None)
    score = score_candidate(s, no_data, as_of=date(2026, 5, 1))
    assert 0.0 <= score <= 1.0


def test_year_built_mismatch_drops_score():
    s = _subject(year_built=1960)
    similar_age = _candidate(year_built=1962)
    different_age = _candidate(year_built=2020)
    sim = score_candidate(s, similar_age, as_of=date(2026, 5, 1))
    diff = score_candidate(s, different_age, as_of=date(2026, 5, 1))
    assert sim > diff