from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.sale import Sale


@pytest.mark.integration
def test_create_sale(db_session, factories):
    sale = factories.Sale()
    db_session.flush()
    assert sale.id is not None
    assert sale.property_id is not None


@pytest.mark.integration
def test_sale_price_nonnegative(db_session, factories):
    prop = factories.Property()
    db_session.flush()

    bad = Sale(
        property_id=prop.id,
        sale_date=date(2024, 1, 1),
        sale_price=-1,
        source_id="test",
        payload_hash="b" * 64,
    )
    db_session.add(bad)
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_sale_requires_property(db_session):
    sale = Sale(
        property_id="00000000-0000-0000-0000-000000000000",
        sale_date=date(2024, 1, 1),
        sale_price=100000,
        source_id="test",
        payload_hash="c" * 64,
    )
    db_session.add(sale)
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_document_number_unique_per_source(db_session, factories):
    prop = factories.Property()
    factories.Sale(property=prop, document_number="DOC-12345", source_id="philly_dor")
    db_session.flush()

    duplicate = Sale(
        property_id=prop.id,
        sale_date=date(2024, 1, 1),
        sale_price=100000,
        document_number="DOC-12345",
        source_id="philly_dor",
        payload_hash="d" * 64,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_document_number_null_allowed_multiple(db_session, factories):
    prop = factories.Property()
    factories.Sale(property=prop, document_number=None)
    factories.Sale(property=prop, document_number=None)
    db_session.flush()


@pytest.mark.integration
def test_document_number_unique_per_source_not_globally(db_session, factories):
    prop = factories.Property()
    factories.Sale(property=prop, document_number="DOC-12345", source_id="philly_dor")
    factories.Sale(property=prop, document_number="DOC-12345", source_id="bucks_recorder")
    db_session.flush()