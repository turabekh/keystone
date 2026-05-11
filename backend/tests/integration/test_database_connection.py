import os

import psycopg
import pytest

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://keystone:keystone_dev@localhost:5436/keystone",
)


@pytest.mark.integration
def test_can_connect_to_postgres():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            assert result == (1,)


@pytest.mark.integration
def test_required_extensions_installed():
    required = {"pg_trgm", "btree_gin", "pgcrypto"}
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT extname FROM pg_extension")
            installed = {row[0] for row in cur.fetchall()}
    assert required.issubset(installed)


@pytest.mark.integration
def test_keystone_schema_exists():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'keystone'"
            )
            assert cur.fetchone() is not None


@pytest.mark.integration
def test_search_path_includes_keystone():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW search_path")
            search_path = cur.fetchone()[0]
            assert "keystone" in search_path