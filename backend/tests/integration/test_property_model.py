import pytest
from sqlalchemy.exc import IntegrityError

from app.models.property import Property, PropertyCategory


def _make_property(**overrides):
    defaults = dict(
        parcel_id="TEST-PARCEL",
        address_full="100 TEST ST",
        address_normalized="100 test st",
        state="PA",
        property_category=PropertyCategory.ROWHOUSE,
        source_id="test",
        payload_hash="a" * 64,
    )
    defaults.update(overrides)
    return Property(**defaults)


@pytest.mark.integration
def test_create_property(db_session, factories):
    prop = factories.Property()
    db_session.flush()
    assert prop.id is not None
    assert prop.property_category == PropertyCategory.ROWHOUSE
    assert prop.created_at is not None


@pytest.mark.integration
def test_property_unique_county_parcel(db_session, factories):
    county = factories.County()
    factories.Property(county=county, parcel_id="DUPLICATE-1")
    db_session.flush()

    duplicate = _make_property(county_id=county.id, parcel_id="DUPLICATE-1")
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_property_same_parcel_different_counties(db_session, factories):
    c1 = factories.County(slug="county-a")
    c2 = factories.County(slug="county-b")
    factories.Property(county=c1, parcel_id="SAME-PARCEL")
    factories.Property(county=c2, parcel_id="SAME-PARCEL")
    db_session.flush()


@pytest.mark.integration
def test_property_state_uppercase(db_session, factories):
    county = factories.County()
    db_session.flush()

    prop = _make_property(county_id=county.id, state="pa")
    db_session.add(prop)
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_property_year_built_range(db_session, factories):
    county = factories.County()
    db_session.flush()

    prop = _make_property(county_id=county.id, year_built=1599)
    db_session.add(prop)
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_property_assessed_nonnegative(db_session, factories):
    county = factories.County()
    db_session.flush()

    prop = _make_property(county_id=county.id, current_assessed_total=-1)
    db_session.add(prop)
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_property_category_enum_enforced(db_session, factories):
    from sqlalchemy import text

    prop = factories.Property()
    db_session.flush()
    with pytest.raises(Exception):
        db_session.execute(
            text("UPDATE keystone.properties SET property_category = 'invalid_category' WHERE id = :id"),
            {"id": prop.id},
        )


@pytest.mark.integration
def test_property_sales_relationship(db_session, factories):
    from datetime import date

    prop = factories.Property()
    s1 = factories.Sale(property=prop, sale_date=date(2020, 1, 1), sale_price=300000)
    s2 = factories.Sale(property=prop, sale_date=date(2023, 6, 15), sale_price=425000)
    db_session.flush()
    db_session.refresh(prop)

    assert len(prop.sales) == 2
    assert prop.sales[0].sale_date == s2.sale_date


@pytest.mark.integration
def test_sale_cascade_on_property_delete(db_session, factories):
    prop = factories.Property()
    sale = factories.Sale(property=prop)
    db_session.flush()
    sale_id = sale.id

    db_session.delete(prop)
    db_session.flush()

    from app.models.sale import Sale
    assert db_session.query(Sale).filter_by(id=sale_id).first() is None


@pytest.mark.integration
def test_county_cannot_be_deleted_with_properties(db_session, factories):
    county = factories.County()
    factories.Property(county=county)
    db_session.flush()

    db_session.delete(county)
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_trigram_index_supports_fuzzy_search(db_session, factories):
    from sqlalchemy import text

    factories.Property(
        address_full="106 OVERHILL AVE PHILADELPHIA PA 19116",
        address_normalized="106 overhill ave philadelphia pa 19116",
    )
    db_session.flush()

    result = db_session.execute(
        text("""
            SELECT address_full
            FROM keystone.properties
            WHERE address_normalized % :query
            ORDER BY similarity(address_normalized, :query) DESC
            LIMIT 5
        """),
        {"query": "overhill philadelphia"},
    ).all()

    addresses = [row[0] for row in result]
    assert any("OVERHILL" in a for a in addresses)