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


@pytest.mark.integration
def test_philadelphia_clr_uses_reassessment_designation_100(db_session):
    stmt = (
        select(CountyYearSetting)
        .join(County)
        .where(County.slug == "philadelphia", CountyYearSetting.tax_year == 2027)
    )
    setting = db_session.scalars(stmt).one()
    assert setting.clr_factor == Decimal("1.00")
    assert setting.clr_ratio == Decimal("100.0000")
    assert setting.effective_tax_rate == Decimal("0.013998")


@pytest.mark.integration
def test_bucks_clr_ratio_matches_steb_2024(db_session):
    stmt = (
        select(CountyYearSetting)
        .join(County)
        .where(County.slug == "bucks", CountyYearSetting.tax_year == 2027)
    )
    setting = db_session.scalars(stmt).one()
    assert setting.clr_factor == Decimal("17.06")
    assert setting.clr_ratio == Decimal("5.8600")
    assert setting.effective_tax_rate == Decimal("0.017300")
    assert setting.clr_sample_size == 6361
    assert setting.last_reassessment_year == 1972


@pytest.mark.integration
def test_montgomery_clr_ratio_matches_steb_2024(db_session):
    stmt = (
        select(CountyYearSetting)
        .join(County)
        .where(County.slug == "montgomery", CountyYearSetting.tax_year == 2027)
    )
    setting = db_session.scalars(stmt).one()
    assert setting.clr_factor == Decimal("3.25")
    assert setting.clr_ratio == Decimal("30.7600")
    assert setting.effective_tax_rate == Decimal("0.014400")
    assert setting.last_reassessment_year == 1996


@pytest.mark.integration
def test_delaware_clr_ratio_matches_steb_2024(db_session):
    stmt = (
        select(CountyYearSetting)
        .join(County)
        .where(County.slug == "delaware", CountyYearSetting.tax_year == 2027)
    )
    setting = db_session.scalars(stmt).one()
    assert setting.clr_factor == Decimal("1.74")
    assert setting.clr_ratio == Decimal("57.3300")
    assert setting.effective_tax_rate == Decimal("0.018600")
    assert setting.clr_sample_size == 6537
    assert setting.last_reassessment_year == 2021


@pytest.mark.integration
def test_chester_clr_ratio_matches_steb_2024(db_session):
    stmt = (
        select(CountyYearSetting)
        .join(County)
        .where(County.slug == "chester", CountyYearSetting.tax_year == 2027)
    )
    setting = db_session.scalars(stmt).one()
    assert setting.clr_factor == Decimal("3.14")
    assert setting.clr_ratio == Decimal("31.8400")
    assert setting.effective_tax_rate == Decimal("0.012500")
    assert setting.clr_sample_size == 5297
    assert setting.last_reassessment_year == 1998


@pytest.mark.integration
def test_all_seeded_counties_have_source_notes(db_session):
    stmt = (
        select(CountyYearSetting)
        .join(County)
        .where(County.state == "PA", CountyYearSetting.tax_year == 2027)
    )
    settings = db_session.scalars(stmt).all()
    assert len(settings) == 5
    for setting in settings:
        assert setting.clr_source_note is not None
        assert "STEB" in setting.clr_source_note or "Philadelphia" in setting.clr_source_note
        assert len(setting.clr_source_note) > 50


@pytest.mark.integration
def test_clr_factor_and_ratio_are_approximately_reciprocal(db_session):
    """STEB factor and ratio are mathematical reciprocals subject to rounding.
    
    Per PA tax law, do not derive one from the other - they're published
    independently and rounding causes ~0.1% drift. This test verifies the drift
    is within tolerance, not that they're exactly equal.
    """
    stmt = (
        select(CountyYearSetting)
        .join(County)
        .where(County.state == "PA", CountyYearSetting.tax_year == 2027)
    )
    settings = db_session.scalars(stmt).all()
    for setting in settings:
        if setting.clr_factor is None or setting.clr_ratio is None:
            continue
        implied_ratio = Decimal("100") / setting.clr_factor
        drift = abs(implied_ratio - setting.clr_ratio)
        assert drift < Decimal("0.5"), (
            f"County setting (id={setting.id}) has factor {setting.clr_factor} "
            f"and ratio {setting.clr_ratio}, implied ratio {implied_ratio:.4f}, "
            f"drift {drift:.4f} exceeds 0.5"
        )