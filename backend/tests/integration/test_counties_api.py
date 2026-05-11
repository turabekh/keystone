import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
def test_health_db(client):
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


@pytest.mark.integration
def test_list_counties_returns_five(client):
    response = client.get("/api/v1/counties/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    slugs = {c["slug"] for c in data}
    assert slugs == {"bucks", "chester", "delaware", "montgomery", "philadelphia"}


@pytest.mark.integration
def test_get_county_by_slug(client):
    response = client.get("/api/v1/counties/PA/bucks")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "bucks"
    assert data["name"] == "Bucks"
    assert len(data["year_settings"]) == 1
    assert data["year_settings"][0]["clr_factor"] == 17.06
    assert data["year_settings"][0]["last_reassessment_year"] == 1972


@pytest.mark.integration
def test_get_county_case_insensitive_state(client):
    response = client.get("/api/v1/counties/pa/bucks")
    assert response.status_code == 200


@pytest.mark.integration
def test_get_county_not_found(client):
    response = client.get("/api/v1/counties/PA/nonexistent")
    assert response.status_code == 404


@pytest.mark.integration
def test_county_includes_filing_office(client):
    response = client.get("/api/v1/counties/PA/philadelphia")
    data = response.json()
    assert data["filing_office_name"] == "Board of Revision of Taxes"
    assert "(215)" in data["filing_office_phone"]