from pathlib import Path
from typing import Any

import yaml

from validation.schema import ExpectedCase


def load_validation_set(yaml_path: Path) -> list[ExpectedCase]:
    """Load expected cases from a YAML file."""
    with yaml_path.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    
    if not data or "cases" not in data:
        return []
    
    return [_build_case(record) for record in data["cases"]]


def _build_case(record: dict[str, Any]) -> ExpectedCase:
    expected_savings = record.get("expected_annual_savings", {})
    point_estimate = record.get("expected_point_estimate", {})
    tags = tuple(record.get("tags", []))
    
    return ExpectedCase(
        test_id=record["test_id"],
        address_query=record["address_query"],
        state=record.get("state", "PA"),
        county_slug=record.get("county_slug", "philadelphia"),
        expected_parcel_id=record.get("expected_parcel_id"),
        expected_address_contains=record.get("expected_address_contains"),
        expected_recommendation=record.get("expected_recommendation"),
        expected_argument=record.get("expected_argument"),
        expected_counter_appeal_risk=record.get("expected_counter_appeal_risk"),
        expected_annual_savings_min=expected_savings.get("min"),
        expected_annual_savings_max=expected_savings.get("max"),
        expected_valuation_confidence=record.get("expected_valuation_confidence"),
        expected_point_estimate_min=point_estimate.get("min"),
        expected_point_estimate_max=point_estimate.get("max"),
        expected_comp_count_min=record.get("expected_comp_count_min"),
        expected_uniformity_signal=record.get("expected_uniformity_signal"),
        notes=record.get("notes", ""),
        tags=tags,
    )