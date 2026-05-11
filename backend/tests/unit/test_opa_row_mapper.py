from datetime import date

import pytest

from app.etl.loaders.philly_opa.row_mapper import (
    MapStats,
    MappedProperty,
    _clean,
    _is_city_owned,
    _normalize_address,
    _to_date,
    _to_decimal,
    _to_int,
    map_row,
)


@pytest.fixture
def sample_row():
    return {
        "parcel_number": "661127300",
        "location": "3626 MORRELL AVE",
        "house_number": "3626",
        "street_direction": "",
        "street_name": "MORRELL",
        "street_designation": "AVE",
        "unit": "",
        "zip_code": "19114-1926",
        "building_code_description": "ROW B/GAR 2 STY MAS+OTHER",
        "category_code_description": "SINGLE FAMILY",
        "year_built": "1961",
        "total_livable_area": "1296",
        "total_area": "6279",
        "number_of_bedrooms": "3",
        "number_of_bathrooms": "1",
        "number_stories": "2",
        "market_value": "302000",
        "taxable_land": "60400",
        "taxable_building": "141600",
        "sale_date": "2026-03-06 00:00:00-05:00",
        "sale_price": "1",
        "owner_1": "AVINGTON CONSTANCE",
        "owner_2": "AVINGTON MARGARET M",
    }


def test_clean_empty_string():
    assert _clean("") is None
    assert _clean("   ") is None


def test_clean_null_strings():
    assert _clean("NULL") is None
    assert _clean("None") is None
    assert _clean("N/A") is None
    assert _clean("null") is None


def test_clean_preserves_value():
    assert _clean(" 123 ") == "123"
    assert _clean("hello") == "hello"


def test_to_int():
    assert _to_int("100") == 100
    assert _to_int("100.0") == 100
    assert _to_int("") is None
    assert _to_int(None) is None
    assert _to_int("abc") is None


def test_to_decimal():
    from decimal import Decimal
    assert _to_decimal("1.5") == Decimal("1.5")
    assert _to_decimal("2") == Decimal("2")
    assert _to_decimal("") is None
    assert _to_decimal("xyz") is None


def test_to_date_iso_with_tz():
    assert _to_date("2026-03-06 00:00:00-05:00") == date(2026, 3, 6)


def test_to_date_iso_simple():
    assert _to_date("2024-01-15") == date(2024, 1, 15)


def test_to_date_invalid():
    assert _to_date("not a date") is None
    assert _to_date("") is None
    assert _to_date(None) is None


def test_normalize_address_lowercase():
    assert _normalize_address("3626 MORRELL AVE") == "3626 morrell ave"


def test_normalize_address_whitespace():
    assert _normalize_address("3626   MORRELL    AVE") == "3626 morrell ave"


def test_normalize_address_none():
    assert _normalize_address(None) == ""


def test_is_city_owned_phila():
    assert _is_city_owned("CITY OF PHILA", None) is True
    assert _is_city_owned("CITY OF PHILADELPHIA", None) is True


def test_is_city_owned_other_govt():
    assert _is_city_owned("PHILADELPHIA HOUSING AUTHORITY", None) is True
    assert _is_city_owned("SCHOOL DISTRICT OF PHILA", None) is True
    assert _is_city_owned("SEPTA", None) is True


def test_is_city_owned_private():
    assert _is_city_owned("SMITH JOHN", None) is False
    assert _is_city_owned("ACME LLC", None) is False


def test_is_city_owned_in_owner_2():
    assert _is_city_owned("PRIVATE OWNER", "CITY OF PHILA") is True


def test_map_row_success(sample_row):
    stats = MapStats()
    result = map_row(sample_row, county_id="00000000-0000-0000-0000-000000000001", stats=stats)

    assert result is not None
    assert isinstance(result, MappedProperty)
    assert result.parcel_id == "661127300"
    assert result.payload["address_full"] == "3626 MORRELL AVE"
    assert result.payload["address_normalized"] == "3626 morrell ave"
    assert result.payload["street_number"] == "3626"
    assert result.payload["street_name"] == "MORRELL"
    assert result.payload["street_suffix"] == "AVE"
    assert result.payload["city"] == "PHILADELPHIA"
    assert result.payload["state"] == "PA"
    assert result.payload["zip_code"] == "19114"
    assert result.payload["year_built"] == 1961
    assert result.payload["current_assessed_total"] == 302000
    assert result.payload["last_sale_date"] == date(2026, 3, 6)
    assert result.payload["property_category"] == "rowhouse"
    assert result.payload["source_id"] == "philly_opa"
    assert len(result.payload["payload_hash"]) == 64

    assert stats.seen == 1
    assert stats.mapped == 1


def test_map_row_skips_no_parcel(sample_row):
    sample_row["parcel_number"] = ""
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result is None
    assert stats.skipped_no_parcel == 1
    assert stats.mapped == 0


def test_map_row_skips_no_market_value(sample_row):
    sample_row["market_value"] = ""
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result is None
    assert stats.skipped_no_market_value == 1


def test_map_row_skips_city_owned(sample_row):
    sample_row["owner_1"] = "CITY OF PHILA"
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result is None
    assert stats.skipped_city_owned == 1


def test_zip_plus_four_truncated(sample_row):
    sample_row["zip_code"] = "19114-1926"
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result.payload["zip_code"] == "19114"


def test_invalid_zip_becomes_none(sample_row):
    sample_row["zip_code"] = "ABCDE"
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result.payload["zip_code"] is None


def test_year_built_out_of_range(sample_row):
    sample_row["year_built"] = "0"
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result.payload["year_built"] is None


def test_year_built_far_future_rejected(sample_row):
    sample_row["year_built"] = "2200"
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result.payload["year_built"] is None


def test_negative_sale_price_becomes_none(sample_row):
    sample_row["sale_price"] = "-1"
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result.payload["last_sale_price"] is None


def test_direction_normalized(sample_row):
    sample_row["street_direction"] = "n."
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result.payload["street_direction"] == "N"


def test_hash_is_stable(sample_row):
    stats1 = MapStats()
    stats2 = MapStats()
    r1 = map_row(sample_row, county_id="x", stats=stats1)
    r2 = map_row(sample_row, county_id="x", stats=stats2)
    assert r1.payload_hash == r2.payload_hash


def test_hash_changes_on_data_change(sample_row):
    stats = MapStats()
    r1 = map_row(sample_row, county_id="x", stats=stats)

    sample_row["market_value"] = "400000"
    r2 = map_row(sample_row, county_id="x", stats=MapStats())
    assert r1.payload_hash != r2.payload_hash


def test_hash_independent_of_county_id(sample_row):
    r1 = map_row(sample_row, county_id="county-a", stats=MapStats())
    r2 = map_row(sample_row, county_id="county-b", stats=MapStats())
    assert r1.payload_hash == r2.payload_hash


def test_raw_data_preserved(sample_row):
    sample_row["objectid"] = "12345"
    sample_row["mailing_zip"] = "19114-1926"
    stats = MapStats()
    result = map_row(sample_row, county_id="x", stats=stats)
    assert result.raw_data["objectid"] == "12345"
    assert result.raw_data["mailing_zip"] == "19114-1926"


def test_real_opa_row_from_sample_data():
    row = {
        "parcel_number": "421352100",
        "location": "4612 C ST",
        "house_number": "4612",
        "street_direction": "",
        "street_name": "C",
        "street_designation": "ST",
        "unit": "",
        "zip_code": "19120",
        "building_code_description": "ROW B/GAR 2 STY MASONRY",
        "category_code_description": "SINGLE FAMILY",
        "year_built": "1942",
        "total_livable_area": "1200",
        "total_area": "1219",
        "number_of_bedrooms": "3",
        "number_of_bathrooms": "1",
        "number_stories": "2",
        "market_value": "139900",
        "taxable_land": "27980",
        "taxable_building": "111920",
        "sale_date": "2026-03-05 00:00:00-05:00",
        "sale_price": "110000",
        "owner_1": "HILLCREST ESTATES & PARTNERS LLC",
        "owner_2": "",
    }
    stats = MapStats()
    result = map_row(row, county_id="x", stats=stats)
    assert result is not None
    assert result.parcel_id == "421352100"
    assert result.payload["property_category"] == "rowhouse"
    assert result.payload["last_sale_price"] == 110000
    assert result.payload["current_assessed_total"] == 139900