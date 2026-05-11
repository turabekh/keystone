import pytest

from app.models.county import County, CountyYearSetting
from app.models.property import Property, PropertyCategory
from app.models.sale import Sale


@pytest.mark.integration
def test_county_factory_produces_valid_row(db_session, factories):
    county = factories.County()
    db_session.flush()
    assert isinstance(county, County)
    assert county.id is not None
    assert county.state == "PA"
    assert county.created_at is not None


@pytest.mark.integration
def test_county_factory_unique_per_call(db_session, factories):
    c1 = factories.County()
    c2 = factories.County()
    db_session.flush()
    assert c1.id != c2.id
    assert c1.slug != c2.slug


@pytest.mark.integration
def test_county_year_setting_factory(db_session, factories):
    setting = factories.CountyYearSetting()
    db_session.flush()
    assert isinstance(setting, CountyYearSetting)
    assert setting.county_id is not None
    assert setting.tax_year == 2026


@pytest.mark.integration
def test_property_factory_produces_valid_row(db_session, factories):
    prop = factories.Property()
    db_session.flush()
    assert isinstance(prop, Property)
    assert prop.id is not None
    assert prop.county_id is not None
    assert prop.state == "PA"
    assert prop.property_category == PropertyCategory.ROWHOUSE


@pytest.mark.integration
def test_property_factory_payload_hash_is_64_chars(db_session, factories):
    prop = factories.Property()
    db_session.flush()
    assert len(prop.payload_hash) == 64


@pytest.mark.integration
def test_property_factory_unique_per_call(db_session, factories):
    p1 = factories.Property()
    p2 = factories.Property()
    db_session.flush()
    assert p1.parcel_id != p2.parcel_id
    assert p1.payload_hash != p2.payload_hash


@pytest.mark.integration
def test_sale_factory_produces_valid_row(db_session, factories):
    sale = factories.Sale()
    db_session.flush()
    assert isinstance(sale, Sale)
    assert sale.id is not None
    assert sale.property_id is not None
    assert sale.sale_price > 0


@pytest.mark.integration
def test_sale_factory_payload_hash_is_64_chars(db_session, factories):
    sale = factories.Sale()
    db_session.flush()
    assert len(sale.payload_hash) == 64