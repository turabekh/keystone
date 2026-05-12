from fastapi.testclient import TestClient

from validation.schema import ExpectedCase, ValidationOutcome


def run_case(client: TestClient, case: ExpectedCase) -> ValidationOutcome:
    """Run one expected case against the engine, comparing against expected values."""
    failures: list[str] = []
    
    # 1. Look up property
    lookup_response = client.get(
        "/api/v1/properties/lookup",
        params={
            "q": case.address_query,
            "state": case.state,
            "county_slug": case.county_slug,
            "limit": 1,
        },
    )
    if lookup_response.status_code != 200:
        return ValidationOutcome(
            case=case,
            passed=False,
            property_id=None,
            failures=[f"Lookup failed: HTTP {lookup_response.status_code}"],
        )
    
    results = lookup_response.json()
    if not results:
        return ValidationOutcome(
            case=case,
            passed=False,
            property_id=None,
            failures=[f"No property found for query: {case.address_query!r}"],
        )
    
    prop = results[0]
    property_id = prop["id"]
    
    # 2. Verify property identification
    if case.expected_parcel_id and prop["parcel_id"] != case.expected_parcel_id:
        failures.append(
            f"Wrong parcel: expected {case.expected_parcel_id}, got {prop['parcel_id']} "
            f"({prop['address_full']})"
        )
    if case.expected_address_contains:
        if case.expected_address_contains.upper() not in prop["address_full"].upper():
            failures.append(
                f"Address mismatch: {prop['address_full']!r} does not contain "
                f"{case.expected_address_contains!r}"
            )
    
    # 3. Run valuation if any valuation fields are expected
    if _wants_valuation_check(case):
        val_response = client.get(f"/api/v1/properties/{property_id}/valuation")
        val_data = val_response.json()
        _check_valuation(case, val_data, failures)
    
    # 4. Run uniformity if expected
    if case.expected_uniformity_signal is not None:
        uni_response = client.get(f"/api/v1/properties/{property_id}/uniformity")
        uni_data = uni_response.json()
        _check_uniformity(case, uni_data, failures)
    
    # 5. Run recommendation (always — this is the core engine output)
    rec_response = client.get(f"/api/v1/properties/{property_id}/recommendation")
    rec_data = rec_response.json()
    _check_recommendation(case, rec_data, failures)
    
    return ValidationOutcome(
        case=case,
        passed=len(failures) == 0,
        property_id=property_id,
        failures=failures,
    )


def _wants_valuation_check(case: ExpectedCase) -> bool:
    return any([
        case.expected_valuation_confidence is not None,
        case.expected_point_estimate_min is not None,
        case.expected_point_estimate_max is not None,
        case.expected_comp_count_min is not None,
    ])


def _check_valuation(case: ExpectedCase, val_data: dict, failures: list[str]) -> None:
    if case.expected_valuation_confidence is not None:
        actual = val_data.get("confidence")
        if actual != case.expected_valuation_confidence:
            failures.append(
                f"Valuation confidence: expected {case.expected_valuation_confidence!r}, "
                f"got {actual!r}"
            )
    
    pt = val_data.get("point_estimate")
    if case.expected_point_estimate_min is not None:
        if pt is None or pt < case.expected_point_estimate_min:
            failures.append(
                f"Point estimate too low: expected ≥${case.expected_point_estimate_min:,}, "
                f"got ${pt if pt else 0:,}"
            )
    if case.expected_point_estimate_max is not None:
        if pt is None or pt > case.expected_point_estimate_max:
            failures.append(
                f"Point estimate too high: expected ≤${case.expected_point_estimate_max:,}, "
                f"got ${pt if pt else 0:,}"
            )
    
    if case.expected_comp_count_min is not None:
        actual = val_data.get("comp_count", 0)
        if actual < case.expected_comp_count_min:
            failures.append(
                f"Comp count too low: expected ≥{case.expected_comp_count_min}, got {actual}"
            )


def _check_uniformity(case: ExpectedCase, uni_data: dict, failures: list[str]) -> None:
    actual = uni_data.get("signal")
    if actual != case.expected_uniformity_signal:
        failures.append(
            f"Uniformity signal: expected {case.expected_uniformity_signal!r}, got {actual!r}"
        )


def _check_recommendation(case: ExpectedCase, rec_data: dict, failures: list[str]) -> None:
    if case.expected_recommendation is not None:
        actual = rec_data.get("recommendation")
        if actual != case.expected_recommendation:
            failures.append(
                f"Recommendation: expected {case.expected_recommendation!r}, got {actual!r}"
            )
    
    if case.expected_argument is not None:
        actual = rec_data.get("primary_argument")
        if actual != case.expected_argument:
            failures.append(
                f"Argument: expected {case.expected_argument!r}, got {actual!r}"
            )
    
    if case.expected_counter_appeal_risk is not None:
        actual = rec_data.get("counter_appeal_risk")
        if actual != case.expected_counter_appeal_risk:
            failures.append(
                f"Counter-appeal risk: expected {case.expected_counter_appeal_risk!r}, "
                f"got {actual!r}"
            )
    
    savings = rec_data.get("annual_tax_savings")
    if case.expected_annual_savings_min is not None:
        if savings is None or savings < case.expected_annual_savings_min:
            failures.append(
                f"Annual savings too low: expected ≥${case.expected_annual_savings_min:,}, "
                f"got ${savings if savings else 0:,}"
            )
    if case.expected_annual_savings_max is not None:
        if savings is None or savings > case.expected_annual_savings_max:
            failures.append(
                f"Annual savings too high: expected ≤${case.expected_annual_savings_max:,}, "
                f"got ${savings if savings else 0:,}"
            )