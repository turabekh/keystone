from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine


@pytest.fixture(scope="session")
def db_engine():
    return engine


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def factories(db_session):
    from tests.factories import (
        CountyFactory,
        CountyYearSettingFactory,
        PropertyFactory,
        SaleFactory,
    )

    for factory_cls in (CountyFactory, CountyYearSettingFactory, PropertyFactory, SaleFactory):
        factory_cls._meta.sqlalchemy_session = db_session

    return type("Factories", (), {
        "County": CountyFactory,
        "CountyYearSetting": CountyYearSettingFactory,
        "Property": PropertyFactory,
        "Sale": SaleFactory,
    })


@pytest.fixture
def sample_address_strings():
    return [
        "106 Overhill Ave, Philadelphia, PA 19116",
        "106 OVERHILL AVENUE PHILADELPHIA PA 19116",
        "106 overhill ave philadelphia pennsylvania",
    ]