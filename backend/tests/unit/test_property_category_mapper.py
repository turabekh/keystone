import pytest

from app.models.property import PropertyCategory
from app.services.property_category_mapper import map_building_code_description


@pytest.mark.parametrize("description,expected", [
    ("ROW B/GAR 2 STY MAS+OTHER", PropertyCategory.ROWHOUSE),
    ("ROW B/GAR 2 STY MASONRY", PropertyCategory.ROWHOUSE),
    ("ROW 2 STY MASONRY", PropertyCategory.ROWHOUSE),
    ("ROW W/DET GAR 3 STY", PropertyCategory.ROWHOUSE),
    ("ROW B/GAR 1 STY", PropertyCategory.ROWHOUSE),
    ("ROW POST WAR", PropertyCategory.ROWHOUSE),
    ("ROW PORCH FRONT", PropertyCategory.ROWHOUSE),
])
def test_rowhouse_variants(description, expected):
    assert map_building_code_description(description) == expected


@pytest.mark.parametrize("description,expected", [
    ("TWIN CONV APT", PropertyCategory.MULTI_FAMILY),
    ("TWIN 2 STY", PropertyCategory.TWIN_SEMI),
    ("SEMI/DET 2 STY MASONRY", PropertyCategory.TWIN_SEMI),
    ("SEMI-DET 3 STY", PropertyCategory.TWIN_SEMI),
])
def test_twin_semi_variants(description, expected):
    assert map_building_code_description(description) == expected


@pytest.mark.parametrize("description,expected", [
    ("DET 2 STY MASONRY", PropertyCategory.SINGLE_FAMILY),
    ("DET W/GAR 2 STY", PropertyCategory.SINGLE_FAMILY),
    ("SINGLE FAMILY DETACHED", PropertyCategory.SINGLE_FAMILY),
])
def test_single_family_variants(description, expected):
    assert map_building_code_description(description) == expected


@pytest.mark.parametrize("description,expected", [
    ("APARTMENT 5+ UNITS", PropertyCategory.MULTI_FAMILY),
    ("ROW CONV APT 3 STY", PropertyCategory.MULTI_FAMILY),
    ("DUPLEX 2 STY", PropertyCategory.MULTI_FAMILY),
    ("ROOMING HOUSE", PropertyCategory.MULTI_FAMILY),
])
def test_multi_family_variants(description, expected):
    assert map_building_code_description(description) == expected


@pytest.mark.parametrize("description,expected", [
    ("CONDO RES 1 STORY", PropertyCategory.CONDO),
    ("CONDOMINIUM HIGH-RISE", PropertyCategory.CONDO),
])
def test_condo_variants(description, expected):
    assert map_building_code_description(description) == expected


@pytest.mark.parametrize("description,expected", [
    ("STR/APT 2 STY MASONRY", PropertyCategory.MIXED_USE),
    ("STORE/APT 3 STY", PropertyCategory.MIXED_USE),
    ("MIXED USE COMM/RES", PropertyCategory.MIXED_USE),
])
def test_mixed_use_variants(description, expected):
    assert map_building_code_description(description) == expected


@pytest.mark.parametrize("description,expected", [
    ("STORE 1 STY", PropertyCategory.COMMERCIAL),
    ("OFFICE BLDG", PropertyCategory.COMMERCIAL),
    ("WAREHOUSE LIGHT INDUSTRIAL", PropertyCategory.COMMERCIAL),
    ("RESTAURANT", PropertyCategory.COMMERCIAL),
    ("AUTO REPAIR SHOP", PropertyCategory.COMMERCIAL),
    ("OFF BLD N/COM W/PKG MASON", PropertyCategory.COMMERCIAL),
    ("OFF BLD COM NO GAR MASON", PropertyCategory.COMMERCIAL),
    ("OFF BLD W/COM GAR MASONRY", PropertyCategory.COMMERCIAL),
    ("SCHOOL 5 STY MASONRY", PropertyCategory.COMMERCIAL),
    ("HEALTH FAC HOSP MAS+OTH", PropertyCategory.COMMERCIAL),
    ("HEALTH FAC CLINIC MASONRY", PropertyCategory.COMMERCIAL),
    ("REST'RNT W/BAR MASONRY", PropertyCategory.COMMERCIAL),
    ("PUB UTIL 2 STY METAL", PropertyCategory.COMMERCIAL),
    ("AMUSE HALL MASONRY", PropertyCategory.COMMERCIAL),
    ("AMUSE THEATRE MASONRY+OTH", PropertyCategory.COMMERCIAL),
])
def test_commercial_variants(description, expected):
    assert map_building_code_description(description) == expected


@pytest.mark.parametrize("description,expected", [
    ("VACANT LAND RESID", PropertyCategory.VACANT),
    ("VACANT LOT", PropertyCategory.VACANT),
])
def test_vacant_variants(description, expected):
    assert map_building_code_description(description) == expected


def test_none_description_uses_category_fallback():
    assert map_building_code_description(None, "SINGLE FAMILY") == PropertyCategory.SINGLE_FAMILY
    assert map_building_code_description(None, "MULTI FAMILY") == PropertyCategory.MULTI_FAMILY
    assert map_building_code_description(None, "VACANT LAND") == PropertyCategory.VACANT


def test_empty_description_uses_category_fallback():
    assert map_building_code_description("", "SINGLE FAMILY") == PropertyCategory.SINGLE_FAMILY


def test_unknown_description_falls_back_to_category():
    assert map_building_code_description("XYZZY UNKNOWN", "SINGLE FAMILY") == PropertyCategory.SINGLE_FAMILY


def test_unknown_description_and_category_returns_other():
    assert map_building_code_description("XYZZY", "ZZZ UNKNOWN") == PropertyCategory.OTHER


def test_all_none_returns_other():
    assert map_building_code_description(None, None) == PropertyCategory.OTHER


def test_case_insensitive():
    assert map_building_code_description("row b/gar 2 sty masonry") == PropertyCategory.ROWHOUSE
    assert map_building_code_description("Row B/Gar 2 Sty Masonry") == PropertyCategory.ROWHOUSE


def test_whitespace_handling():
    assert map_building_code_description("  ROW 2 STY MASONRY  ") == PropertyCategory.ROWHOUSE


def test_real_opa_descriptions_from_sample_data():
    samples = [
        ("ROW B/GAR 2 STY MAS+OTHER", PropertyCategory.ROWHOUSE),
        ("ROW B/GAR 2 STY MASONRY", PropertyCategory.ROWHOUSE),
        ("ROW 2 STY MASONRY", PropertyCategory.ROWHOUSE),
    ]
    for description, expected in samples:
        assert map_building_code_description(description) == expected, f"Failed: {description}"


def test_mixed_use_takes_precedence_over_apt_keyword():
    assert map_building_code_description("STR/APT 2 STY") == PropertyCategory.MIXED_USE


def test_rowhouse_with_apt_keyword_becomes_multi_family():
    assert map_building_code_description("ROW CONV APT 3 STY") == PropertyCategory.MULTI_FAMILY


def test_twin_with_apt_keyword_becomes_multi_family():
    assert map_building_code_description("TWIN CONV APT") == PropertyCategory.MULTI_FAMILY