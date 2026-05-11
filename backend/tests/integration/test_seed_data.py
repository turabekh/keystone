import pytest
from sqlalchemy import select
from decimal import Decimal


from app.models.county import County, CountyYearSetting


@pytest.mark.integration
def test_pa_counties_seeded(db_session):
    stmt = select(County).where(County.state == "PA").order_by(County.name)
    counties = db_session.scalars(stmt).all()
    slugs = [c.slug for c in counties]
    assert slugs == ["bucks", "chester", "delaware", "montgomery", "philadelphia"]


@pytest.mark.integration
def test_bucks_has_high_clr_factor(db_session):
    stmt = (
        select(CountyYearSetting)
        .join(County)
        .where(County.slug == "bucks", CountyYearSetting.tax_year == 2027)
    )
    setting = db_session.scalars(stmt).one()
    assert setting.clr_factor == Decimal("17.06")
    assert setting.last_reassessment_year == 1972


@pytest.mark.integration
def test_each_county_has_2027_settings(db_session):
    stmt = (
        select(County.slug)
        .join(CountyYearSetting)
        .where(County.state == "PA", CountyYearSetting.tax_year == 2027)
    )
    slugs = set(db_session.scalars(stmt).all())
    assert slugs == {"philadelphia", "bucks", "montgomery", "delaware", "chester"}


@pytest.mark.integration
def test_all_counties_have_filing_office(db_session):
    stmt = select(County).where(County.state == "PA")
    counties = db_session.scalars(stmt).all()
    for c in counties:
        assert c.filing_office_name is not None
        assert c.filing_office_address is not None
        assert c.filing_office_phone is not None