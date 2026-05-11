import time

import pytest
from sqlalchemy.exc import IntegrityError, DataError

from app.models.county import County, CountyYearSetting


@pytest.mark.integration
def test_create_county(db_session, factories):
    county = factories.County()
    db_session.flush()
    assert county.id is not None
    assert county.created_at is not None
    assert county.updated_at is not None


@pytest.mark.integration
def test_county_state_must_be_uppercase(db_session):
    db_session.add(County(name="Chester", state="pa", slug="chester"))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_county_state_length_constraint(db_session):
    db_session.add(County(name="Chester", state="PAA", slug="chester"))
    with pytest.raises((DataError, IntegrityError)):
        db_session.flush()



@pytest.mark.integration
def test_unique_state_slug(db_session, factories):
    factories.County(state="PA", slug="chester")
    db_session.flush()
    db_session.add(County(name="Chester Two", state="PA", slug="chester"))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_county_year_setting_relationship(db_session, factories):
    county = factories.County()
    setting = factories.CountyYearSetting(county=county, tax_year=2026, clr_factor=17.06)
    db_session.flush()
    assert setting.county_id == county.id
    assert setting in county.year_settings


@pytest.mark.integration
def test_year_setting_cascade_delete(db_session, factories):
    county = factories.County()
    setting = factories.CountyYearSetting(county=county)
    db_session.flush()
    setting_id = setting.id
    db_session.delete(county)
    db_session.flush()
    result = db_session.query(CountyYearSetting).filter_by(id=setting_id).first()
    assert result is None


@pytest.mark.integration
def test_clr_must_be_positive(db_session, factories):
    county = factories.County()
    db_session.flush()
    db_session.add(CountyYearSetting(county_id=county.id, tax_year=2026, clr_factor=-1))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_updated_at_trigger(db_session, factories):
    county = factories.County()
    db_session.commit()
    db_session.refresh(county)
    original = county.updated_at

    time.sleep(1.1)

    county.name = "Renamed"
    db_session.commit()
    db_session.refresh(county)
    assert county.updated_at > original


@pytest.mark.integration
def test_unique_county_year(db_session, factories):
    county = factories.County()
    db_session.flush()
    factories.CountyYearSetting(county=county, tax_year=2026, clr_factor=30.0)
    db_session.flush()
    db_session.add(CountyYearSetting(county_id=county.id, tax_year=2026, clr_factor=31.0))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_tax_year_range_constraint(db_session, factories):
    county = factories.County()
    db_session.flush()
    db_session.add(CountyYearSetting(county_id=county.id, tax_year=1999, clr_factor=30.0))
    with pytest.raises(IntegrityError):
        db_session.flush()