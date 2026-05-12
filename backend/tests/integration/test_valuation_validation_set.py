import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _lookup_first(client, query: str) -> dict | None:
    response = client.get(
        "/api/v1/properties/lookup",
        params={"q": query, "state": "PA", "county_slug": "philadelphia", "limit": 1},
    )
    assert response.status_code == 200
    results = response.json()
    return results[0] if results else None


@pytest.mark.integration
def test_1204_master_st_rowhouse_valuation(client):
    """1204 MASTER ST: Brewerytown rowhouse, ~$250K range, used as canonical happy-path."""
    prop = _lookup_first(client, "1204 master")
    assert prop is not None
    response = client.get(f"/api/v1/properties/{prop['id']}/valuation")
    assert response.status_code == 200
    data = response.json()
    assert data["confidence"] in {"high", "medium"}
    assert data["comp_count"] >= 5
    assert 200_000 <= data["point_estimate"] <= 320_000


@pytest.mark.integration
def test_106_overhill_ave_single_family_valuation(client):
    """106 OVERHILL AVE: NE Philly single-family, known to over-estimate ~10% in v1.
    Redfin estimate is $560K; engine produces ~$616K. Locked in as known limitation."""
    prop = _lookup_first(client, "106 overhill")
    assert prop is not None
    response = client.get(f"/api/v1/properties/{prop['id']}/valuation")
    assert response.status_code == 200
    data = response.json()
    assert data["confidence"] in {"high", "medium"}
    assert data["comp_count"] >= 5
    assert 500_000 <= data["point_estimate"] <= 700_000


@pytest.mark.integration
def test_vacant_property_returns_insufficient_data(client):
    """Vacant lot: should decline cleanly."""
    prop = _lookup_first(client, "2100 north broad")
    assert prop is not None
    response = client.get(f"/api/v1/properties/{prop['id']}/valuation")
    assert response.status_code == 200
    data = response.json()
    assert data["confidence"] == "insufficient_data"
    assert data["point_estimate"] is None


@pytest.mark.integration
def test_commercial_property_declines_in_v1(client):
    """Commercial property: should return insufficient_data with explanatory note."""
    prop = _lookup_first(client, "1234 frankford")
    if prop is None or prop["property_category"] != "commercial":
        pytest.skip("Test requires a commercial property in DB")
    response = client.get(f"/api/v1/properties/{prop['id']}/valuation")
    assert response.status_code == 200
    data = response.json()
    assert data["confidence"] == "insufficient_data"
    assert any("commercial" in n.lower() or "mixed-use" in n.lower() for n in data["notes"])