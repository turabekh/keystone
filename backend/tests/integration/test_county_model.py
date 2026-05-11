import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.county import County, CountyYearSetting


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.mark.integration
def test_create_county(db_session):
    county = County(name="Chester", state="PA", slug="chester")
    db_session.add(county)
    db_session.commit()
    assert county.id is not None
    assert county.created_at is not None
    assert county.updated_at is not None
    db_session.delete(county)
    db_session.commit()


@pytest.mark.integration
def test_county_state_must_be_uppercase(db_session):
    county = County(name="Chester", state="pa", slug="chester")
    db_session.add(county)
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.integration
def test_county_state_length_constraint(db_session):
    county = County(name="Chester", state="PAA", slug="chester")
    db_session.add(county)
    with pytest.raises((IntegrityError, Exception)):
        db_session.commit()


@pytest.mark.integration
def test_unique_state_slug(db_session):
    c1 = County(name="Chester", state="PA", slug="chester")
    db_session.add(c1)
    db_session.commit()
    c2 = County(name="Chester Two", state="PA", slug="chester")
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    db_session.delete(c1)
    db_session.commit()


@pytest.mark.integration
def test_county_year_setting_relationship(db_session):
    county = County(name="Bucks", state="PA", slug="bucks")
    setting = CountyYearSetting(tax_year=2026, clr_factor=17.06)
    county.year_settings.append(setting)
    db_session.add(county)
    db_session.commit()
    assert setting.county_id == county.id
    assert setting.id is not None
    db_session.delete(county)
    db_session.commit()
    result = db_session.query(CountyYearSetting).filter_by(id=setting.id).first()
    assert result is None


@pytest.mark.integration
def test_clr_must_be_positive(db_session):
    county = County(name="Bucks", state="PA", slug="bucks")
    db_session.add(county)
    db_session.flush()
    setting = CountyYearSetting(county_id=county.id, tax_year=2026, clr_factor=-1)
    db_session.add(setting)
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.integration
def test_updated_at_trigger(db_session):
    import time

    county = County(name="Delaware", state="PA", slug="delaware")
    db_session.add(county)
    db_session.commit()
    db_session.refresh(county)
    original_updated = county.updated_at

    time.sleep(1.1)

    county.name = "Delaware Two"
    db_session.commit()
    db_session.refresh(county)
    assert county.updated_at > original_updated

    db_session.delete(county)
    db_session.commit()


@pytest.mark.integration
def test_unique_county_year(db_session):
    county = County(name="Montgomery", state="PA", slug="montgomery")
    db_session.add(county)
    db_session.flush()

    s1 = CountyYearSetting(county_id=county.id, tax_year=2026, clr_factor=30.76)
    db_session.add(s1)
    db_session.commit()

    s2 = CountyYearSetting(county_id=county.id, tax_year=2026, clr_factor=31.0)
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.delete(county)
    db_session.commit()