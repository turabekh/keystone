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


@pytest.mark.integration
def test_1204_master_uniformity_moderate_case(client):
    """1204 MASTER ST: 10% over-assessed vs neighborhood, moderate appeal case."""
    prop = _lookup_first(client, "1204 master")
    response = client.get(f"/api/v1/properties/{prop['id']}/uniformity")
    assert response.status_code == 200
    data = response.json()
    assert data["signal"] in {"moderate_case", "strong_case"}
    assert data["subject_asr"] > 1.2
    assert data["neighborhood_sample_size"] >= 8


@pytest.mark.integration
def test_106_overhill_uniformity_no_case(client):
    """106 OVERHILL: under-assessed vs neighborhood — should not appeal."""
    prop = _lookup_first(client, "106 overhill")
    response = client.get(f"/api/v1/properties/{prop['id']}/uniformity")
    assert response.status_code == 200
    data = response.json()
    assert data["signal"] == "no_case"
    assert data["subject_asr"] < 0.9


@pytest.mark.integration
def test_7000_emlen_uniformity_strong_case(client):
    """7000 EMLEN ST: 42% over-assessed vs neighborhood — strong appeal case.
    
    This is the canonical 'strong case' validation property. If this regresses
    below 'strong_case' signal, the uniformity engine has changed materially."""
    prop = _lookup_first(client, "7000 emlen")
    response = client.get(f"/api/v1/properties/{prop['id']}/uniformity")
    assert response.status_code == 200
    data = response.json()
    assert data["signal"] == "strong_case"
    assert data["subject_asr"] > 1.2
    assert data["neighborhood_median_asr"] < 1.0
    assert data["deviation_from_neighborhood"] > 0.30


@pytest.mark.integration
def test_uniformity_returns_insufficient_when_few_sales(client):
    """Multi-family in 19138 has too few sales — engine should decline rather than guess."""
    prop = _lookup_first(client, "1500 walnut")
    if prop is None or prop["property_category"] != "multi_family":
        pytest.skip("Test requires multi-family property in DB")
    response = client.get(f"/api/v1/properties/{prop['id']}/uniformity")
    assert response.status_code == 200
    data = response.json()
    assert data["signal"] == "insufficient_data"


@pytest.mark.integration
def test_1204_master_recommendation_appeal(client):
    """1204 MASTER: moderate appeal case with meaningful savings."""
    prop = _lookup_first(client, "1204 master")
    response = client.get(f"/api/v1/properties/{prop['id']}/recommendation")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] in {"appeal", "appeal_strongly"}
    assert data["annual_tax_savings"] >= 500
    assert data["counter_appeal_risk"] == "low"


@pytest.mark.integration
def test_106_overhill_recommendation_no_appeal(client):
    """106 OVERHILL: under-assessed; engine must protect customer from bad appeal."""
    prop = _lookup_first(client, "106 overhill")
    response = client.get(f"/api/v1/properties/{prop['id']}/recommendation")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "do_not_appeal"


@pytest.mark.integration
def test_7000_emlen_recommendation_appeal_strongly(client):
    """7000 EMLEN: canonical strong-case property — 42% uniformity deviation, low counter-appeal risk."""
    prop = _lookup_first(client, "7000 emlen")
    response = client.get(f"/api/v1/properties/{prop['id']}/recommendation")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "appeal_strongly"
    assert data["primary_argument"] == "uniformity"
    assert data["annual_tax_savings"] >= 2000
    assert data["counter_appeal_risk"] == "low"


@pytest.mark.integration
def test_8200_germantown_condo_recommendation_protected(client):
    """8200 GERMANTOWN condo: comp engine has known gaps for high-end condos.
    
    Even though our valuation suggests massive savings, the engine MUST flag this as
    high counter-appeal risk and refuse to recommend appeal. Customer safety is
    non-negotiable — bad recommendations cost real money in counter-appealed taxes."""
    prop = _lookup_first(client, "8200 germantown")
    response = client.get(f"/api/v1/properties/{prop['id']}/recommendation")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "do_not_appeal"
    assert data["counter_appeal_risk"] == "high"
    assert data["annual_tax_savings"] in {0, None}


@pytest.mark.integration
def test_1204_master_size_matched_valuation(client):
    """1204 MASTER: rowhouse, tight-band comps, around $241K post-fix."""
    prop = _lookup_first(client, "1204 master")
    response = client.get(f"/api/v1/properties/{prop['id']}/valuation")
    data = response.json()
    assert 220_000 <= data["point_estimate"] <= 280_000
    tight_comps = [c for c in data["comps"] if c["size_match"] == "tight"]
    assert len(tight_comps) >= 5


@pytest.mark.integration
def test_106_overhill_size_matched_valuation(client):
    """106 OVERHILL AVE: NE Philly single-family.
    
    OPA reports 2,488 sqft; Redfin reports 2,938. We use OPA's number which is
    the BRT's source of truth. With size-bracketed comps from same census tract,
    estimate lands around $613K.
    
    Important: this estimate is HIGHER than the assessment ($471K), confirming
    the property is under-assessed and the engine correctly recommends DO_NOT_APPEAL."""
    prop = _lookup_first(client, "106 overhill")
    response = client.get(f"/api/v1/properties/{prop['id']}/valuation")
    data = response.json()
    assert 550_000 <= data["point_estimate"] <= 680_000
    tight_comps = [c for c in data["comps"] if c["size_match"] == "tight"]
    assert len(tight_comps) >= 5


@pytest.mark.integration
def test_7000_emlen_ward_noise_declined(client):
    """7000 EMLEN: ward-fallback comp pool spans $76-$530/sqft.
    
    Engine MUST refuse to produce a comp-based estimate when same-ward comps
    show extreme variance. The uniformity engine still produces a valid signal,
    and the recommendation should remain APPEAL_STRONGLY based on uniformity alone."""
    prop = _lookup_first(client, "7000 emlen")
    response = client.get(f"/api/v1/properties/{prop['id']}/valuation")
    val_data = response.json()
    assert val_data["confidence"] == "insufficient_data"
    assert val_data["point_estimate"] is None
    
    response = client.get(f"/api/v1/properties/{prop['id']}/recommendation")
    rec_data = response.json()
    assert rec_data["recommendation"] == "appeal_strongly"
    assert rec_data["primary_argument"] == "uniformity"
    assert rec_data["annual_tax_savings"] >= 2000


@pytest.mark.integration
def test_8200_germantown_condo_protected(client):
    """8200 GERMANTOWN: condo with known coverage gaps.
    
    Even after the size-bracketed comp engine produces a number, the
    recommendation MUST be DO_NOT_APPEAL due to high counter-appeal risk
    for condos with no recent subject sale."""
    prop = _lookup_first(client, "8200 germantown")
    response = client.get(f"/api/v1/properties/{prop['id']}/recommendation")
    data = response.json()
    assert data["recommendation"] == "do_not_appeal"
    assert data["counter_appeal_risk"] == "high"