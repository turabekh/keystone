import pytest

from app.services.address_parser import Confidence, ParsedAddress, parse


def test_parse_clean_full_address():
    result = parse("106 Overhill Ave, Philadelphia, PA 19116")
    assert result.is_parseable is True
    assert result.confidence == Confidence.HIGH
    assert result.street_number == "106"
    assert result.street_name == "Overhill"
    assert result.street_suffix == "Ave"
    assert result.city == "Philadelphia"
    assert result.state == "PA"
    assert result.zip_code == "19116"


def test_parse_uppercase_address():
    result = parse("106 OVERHILL AVE PHILADELPHIA PA 19116")
    assert result.is_parseable is True
    assert result.street_number == "106"
    assert result.state == "PA"
    assert result.zip_code == "19116"


def test_parse_minimal_address():
    result = parse("106 Overhill Ave")
    assert result.is_parseable is True
    assert result.confidence == Confidence.MEDIUM
    assert result.street_number == "106"
    assert result.street_name == "Overhill"
    assert result.state is None
    assert result.zip_code is None


def test_parse_empty_string():
    result = parse("")
    assert result.is_parseable is False
    assert result.confidence == Confidence.LOW
    assert result.normalized == ""


def test_parse_whitespace_only():
    result = parse("   ")
    assert result.is_parseable is False


def test_parse_gibberish():
    result = parse("xyzzy frobnicate")
    assert result.is_parseable is False


def test_normalized_is_lowercase():
    result = parse("106 OVERHILL AVE PHILADELPHIA PA 19116")
    assert result.normalized == "106 overhill ave philadelphia pa 19116"


def test_normalized_collapses_whitespace():
    result = parse("106   Overhill    Ave")
    assert "  " not in result.normalized
    assert result.normalized == "106 overhill ave"


def test_zip_plus_four_truncated():
    result = parse("106 Overhill Ave, Philadelphia, PA 19116-1234")
    assert result.zip_code == "19116"


def test_invalid_zip_rejected():
    result = parse("106 Overhill Ave, Philadelphia, PA ABCDE")
    assert result.zip_code is None


def test_invalid_state_rejected():
    result = parse("106 Main St, Somewhere, ZZ 12345")
    assert result.state is None


def test_state_uppercased():
    result = parse("106 Main St, Phila, pa 19116")
    assert result.state == "PA"


def test_pre_directional():
    result = parse("100 N Main St, Phila, PA 19116")
    assert result.street_direction == "N"
    assert result.street_number == "100"


def test_post_directional():
    result = parse("100 Main St N, Phila, PA 19116")
    assert result.street_direction == "N"


def test_directional_uppercased():
    result = parse("100 n. main st, phila, PA 19116")
    assert result.street_direction == "N"


def test_unit_with_apt_keyword():
    result = parse("100 Main St APT 4B, Phila, PA 19116")
    assert result.unit == "4B"


def test_unit_with_hash():
    result = parse("100 Main St #4B, Phila, PA 19116")
    assert result.unit == "4B"


def test_unit_fallback_no_keyword():
    result = parse("100 Main St 4B Phila PA 19116")
    assert result.unit == "4B"


def test_confidence_high_requires_all_fields():
    result = parse("106 Overhill Ave, Philadelphia, PA 19116")
    assert result.confidence == Confidence.HIGH


def test_confidence_medium_without_zip():
    result = parse("106 Overhill Ave, Philadelphia, PA")
    assert result.confidence == Confidence.MEDIUM


def test_confidence_low_no_address():
    result = parse("just some text")
    assert result.confidence == Confidence.LOW


def test_caching_returns_same_object():
    r1 = parse("106 Overhill Ave, Philadelphia, PA 19116")
    r2 = parse("106 Overhill Ave, Philadelphia, PA 19116")
    assert r1 is r2


def test_parsed_address_is_immutable():
    result = parse("106 Overhill Ave")
    with pytest.raises(Exception):
        result.street_number = "999"


def test_parsed_address_is_hashable():
    result = parse("106 Overhill Ave, Philadelphia, PA 19116")
    s = {result}
    assert result in s


@pytest.mark.parametrize("addr,expected_number", [
    ("100 Main St, Phila, PA 19116", "100"),
    ("1 Main St", "1"),
    ("12345 Main St", "12345"),
    ("100A Main St, Phila, PA 19116", "100A"),
])
def test_address_numbers_variety(addr, expected_number):
    result = parse(addr)
    assert result.street_number == expected_number


@pytest.mark.parametrize("addr", [
    "106 Overhill Ave Philadelphia PA 19116",
    "106 OVERHILL AVENUE, PHILADELPHIA, PENNSYLVANIA 19116",
])
def test_known_real_addresses_parse(addr):
    result = parse(addr)
    assert result.is_parseable is True
    assert result.street_number == "106"