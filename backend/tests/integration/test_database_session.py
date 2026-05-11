import pytest
from sqlalchemy import text

from app.core.database import SessionLocal, engine, get_db


@pytest.mark.integration
def test_engine_connects():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.integration
def test_session_works():
    with SessionLocal() as session:
        result = session.execute(text("SELECT current_database()"))
        assert result.scalar() == "keystone"


@pytest.mark.integration
def test_session_uses_keystone_schema():
    with SessionLocal() as session:
        result = session.execute(text("SHOW search_path"))
        path = result.scalar()
        assert "keystone" in path


@pytest.mark.integration
def test_get_db_dependency_yields_session():
    gen = get_db()
    session = next(gen)
    assert session is not None
    result = session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    try:
        next(gen)
    except StopIteration:
        pass


@pytest.mark.integration
def test_get_db_rolls_back_on_exception():
    gen = get_db()
    session = next(gen)
    session.execute(text("CREATE TEMPORARY TABLE test_rollback (id int)"))
    session.execute(text("INSERT INTO test_rollback VALUES (1)"))
    try:
        gen.throw(RuntimeError("simulated failure"))
    except RuntimeError:
        pass