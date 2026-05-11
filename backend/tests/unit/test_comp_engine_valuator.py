from datetime import date
from uuid import uuid4

import pytest

from app.services.comp_engine.types import CompGeographicScope, CompUsed, ValuationConfidence
from app.services.comp_engine.valuator import (
    MIN_PPSF_FLOOR_RESIDENTIAL,
    _adjust_for_time,
    _classify_confidence,
    _filter_outliers,
    _months_between,
    _percentile,
)


def _make_comp(ppsf: float, scope: CompGeographicScope = CompGeographicScope.SAME_BLOCK) -> CompUsed:
    return CompUsed(
        property_id=uuid4(),
        address_full=f"{int(ppsf)} TEST ST",
        parcel_id=f"P-{int(ppsf)}",
        sale_date=date(2025, 1, 1),
        sale_price=int(ppsf * 1000),
        sale_price_adjusted=int(ppsf * 1000),
        living_area=1000,
        price_per_sqft=ppsf,
        similarity_score=0.8,
        geographic_scope=scope,
        months_ago=12,
    )


def test_percentile_basic():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _percentile(values, 0.5) == 3.0
    assert _percentile(values, 0.0) == 1.0
    assert _percentile(values, 1.0) == 5.0


def test_percentile_interpolates():
    values = [10.0, 20.0]
    assert _percentile(values, 0.5) == 15.0


def test_percentile_empty():
    assert _percentile([], 0.5) == 0.0


def test_months_between():
    assert _months_between(date(2025, 1, 1), date(2026, 1, 1)) == 12
    assert _months_between(date(2025, 6, 15), date(2026, 1, 15)) == 7
    assert _months_between(date(2026, 1, 1), date(2025, 1, 1)) == 0


def test_adjust_for_time_no_appreciation():
    assert _adjust_for_time(100000, 12, 0.0) == 100000


def test_adjust_for_time_annual_rate():
    adjusted = _adjust_for_time(100000, 12, 0.05)
    assert 104999 <= adjusted <= 105001


def test_adjust_for_time_partial_year():
    adjusted = _adjust_for_time(100000, 6, 0.10)
    assert 104880 <= adjusted <= 104882


def test_filter_outliers_removes_distress_below_floor():
    ppsf = [30.0, 100.0, 150.0, 200.0, 250.0]
    comps = [_make_comp(p) for p in ppsf]
    clean_ppsf, clean_comps, removed = _filter_outliers(ppsf, comps)
    assert 30.0 not in clean_ppsf
    assert removed == 1
    assert len(clean_comps) == 4


def test_filter_outliers_removes_iqr_outliers():
    ppsf = [100.0, 110.0, 120.0, 125.0, 130.0, 135.0, 140.0, 500.0]
    comps = [_make_comp(p) for p in ppsf]
    clean_ppsf, clean_comps, removed = _filter_outliers(ppsf, comps)
    assert 500.0 not in clean_ppsf
    assert removed >= 1


def test_filter_outliers_keeps_normal_distribution():
    ppsf = [180.0, 190.0, 200.0, 210.0, 220.0, 230.0, 240.0, 250.0]
    comps = [_make_comp(p) for p in ppsf]
    clean_ppsf, clean_comps, removed = _filter_outliers(ppsf, comps)
    assert removed == 0
    assert len(clean_ppsf) == 8


def test_filter_outliers_with_few_comps_skips_iqr():
    ppsf = [100.0, 200.0, 500.0]
    comps = [_make_comp(p) for p in ppsf]
    clean_ppsf, clean_comps, removed = _filter_outliers(ppsf, comps)
    assert 500.0 in clean_ppsf  # IQR skipped when <4 comps
    assert removed == 0


def test_classify_confidence_high_requires_same_block():
    comps = [_make_comp(200.0, CompGeographicScope.SAME_BLOCK) for _ in range(8)]
    assert _classify_confidence(8, comps) == ValuationConfidence.HIGH


def test_classify_confidence_medium_without_block_concentration():
    comps = [_make_comp(200.0, CompGeographicScope.SAME_CENSUS_TRACT) for _ in range(8)]
    assert _classify_confidence(8, comps) == ValuationConfidence.MEDIUM


def test_classify_confidence_low_few_comps():
    comps = [_make_comp(200.0, CompGeographicScope.SAME_CENSUS_TRACT) for _ in range(3)]
    assert _classify_confidence(3, comps) == ValuationConfidence.LOW


def test_classify_confidence_insufficient_data():
    comps = [_make_comp(200.0) for _ in range(2)]
    assert _classify_confidence(2, comps) == ValuationConfidence.INSUFFICIENT_DATA