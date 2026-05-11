import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
def test_lookup_requires_query(client):
    response = client.get("/api/v1/properties/lookup?state=PA&county_slug=philadelphia")
    assert response.status_code == 422


@pytest.mark.integration
def test_lookup_requires_state(client):
    response = client.get("/api/v1/properties/lookup?q=market&county_slug=philadelphia")
    assert response.status_code == 422


@pytest.mark.integration
def test_lookup_requires_county_slug(client):
    response = client.get("/api/v1/properties/lookup?q=market&state=PA")
    assert response.status_code == 422


@pytest.mark.integration
def test_lookup_min_length_three(client):
    response = client.get(
        "/api/v1/properties/lookup",
        params={"q": "ab", "state": "PA", "county_slug": "philadelphia"},
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_lookup_unknown_county_returns_404(client):
    response = client.get(
        "/api/v1/properties/lookup",
        params={"q": "market", "state": "PA", "county_slug": "nonexistent"},
    )
    assert response.status_code == 404


@pytest.mark.integration
def test_lookup_returns_results_for_real_address(client):
    response = client.get(
        "/api/v1/properties/lookup",
        params={"q": "market street", "state": "PA", "county_slug": "philadelphia", "limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "id" in first
    assert "address_full" in first
    assert "similarity" in first
    assert 0.0 <= first["similarity"] <= 1.0
    assert "MARKET" in first["address_full"].upper()


@pytest.mark.integration
def test_lookup_returns_empty_for_gibberish(client):
    response = client.get(
        "/api/v1/properties/lookup",
        params={"q": "xyzzyfrobnicateblarghquux", "state": "PA", "county_slug": "philadelphia"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
def test_lookup_then_detail(client):
    lookup = client.get(
        "/api/v1/properties/lookup",
        params={"q": "market", "state": "PA", "county_slug": "philadelphia", "limit": 1},
    )
    assert lookup.status_code == 200
    results = lookup.json()
    assert len(results) >= 1
    property_id = results[0]["id"]

    detail = client.get(f"/api/v1/properties/{property_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["id"] == property_id
    assert data["state"] == "PA"
    assert "sales" in data
    assert isinstance(data["sales"], list)


@pytest.mark.integration
def test_detail_returns_404_for_missing(client):
    from uuid import uuid4
    response = client.get(f"/api/v1/properties/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.integration
def test_detail_returns_422_for_invalid_uuid(client):
    response = client.get("/api/v1/properties/not-a-uuid")
    assert response.status_code == 422


@pytest.mark.integration
def test_valuation_endpoint_for_real_property(client):
    lookup = client.get(
        "/api/v1/properties/lookup",
        params={"q": "1204 master", "state": "PA", "county_slug": "philadelphia", "limit": 1},
    )
    assert lookup.status_code == 200
    results = lookup.json()
    if not results:
        pytest.skip("No matching property in DB for valuation smoke test")
    property_id = results[0]["id"]

    response = client.get(f"/api/v1/properties/{property_id}/valuation")
    assert response.status_code == 200
    data = response.json()
    assert "point_estimate" in data
    assert "confidence" in data
    assert "comps" in data
    assert data["subject_property_id"] == property_id
    assert data["confidence"] in {"high", "medium", "low", "insufficient_data"}


@pytest.mark.integration
def test_valuation_returns_404_for_missing_property(client):
    from uuid import uuid4
    response = client.get(f"/api/v1/properties/{uuid4()}/valuation")
    assert response.status_code == 404