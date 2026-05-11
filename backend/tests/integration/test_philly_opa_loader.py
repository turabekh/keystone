import csv
import textwrap
from pathlib import Path

import pytest
from sqlalchemy import select, text

from app.etl import run_loader
from app.etl.loaders.philly_opa.loader import PhillyOpaLoader, load_philly_opa
from app.models.county import County
from app.models.property import Property, PropertyCategory


SAMPLE_ROWS = [
    {
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
    },
    {
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
    },
    {
        "parcel_number": "999999999",
        "location": "100 MAIN ST",
        "house_number": "100",
        "street_direction": "",
        "street_name": "MAIN",
        "street_designation": "ST",
        "unit": "",
        "zip_code": "19101",
        "building_code_description": "VACANT LAND",
        "category_code_description": "VACANT LAND",
        "year_built": "",
        "total_livable_area": "0",
        "total_area": "1000",
        "number_of_bedrooms": "0",
        "number_of_bathrooms": "0",
        "number_stories": "0",
        "market_value": "50000",
        "taxable_land": "50000",
        "taxable_building": "0",
        "sale_date": "",
        "sale_price": "",
        "owner_1": "CITY OF PHILADELPHIA",
        "owner_2": "",
    },
    {
        "parcel_number": "555555555",
        "location": "999 NOWHERE LN",
        "house_number": "999",
        "street_direction": "",
        "street_name": "NOWHERE",
        "street_designation": "LN",
        "unit": "",
        "zip_code": "19999",
        "building_code_description": "ROW 2 STY MASONRY",
        "category_code_description": "SINGLE FAMILY",
        "year_built": "1950",
        "total_livable_area": "1100",
        "total_area": "1200",
        "number_of_bedrooms": "2",
        "number_of_bathrooms": "1",
        "number_stories": "2",
        "market_value": "",
        "taxable_land": "",
        "taxable_building": "",
        "sale_date": "",
        "sale_price": "",
        "owner_1": "NOBODY",
        "owner_2": "",
    },
]


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "opa_sample.csv"
    fieldnames = list(SAMPLE_ROWS[0].keys())
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(SAMPLE_ROWS)
    return csv_path


@pytest.fixture
def philly_county_id(db_session) -> str:
    stmt = select(County).where(County.slug == "philadelphia", County.state == "PA")
    county = db_session.scalars(stmt).one()
    return str(county.id)


@pytest.mark.integration
def test_loader_resolves_county(db_session, sample_csv):
    loader = load_philly_opa(db_session, sample_csv)
    assert loader.source_id == "philly_opa"
    assert loader.county_id is not None


@pytest.mark.integration
def test_loader_raises_on_missing_county(db_session, sample_csv):
    with pytest.raises(ValueError, match="County not found"):
        load_philly_opa(db_session, sample_csv, county_slug="nonexistent")


@pytest.mark.integration
def test_loader_inserts_valid_properties(db_session, sample_csv, philly_county_id):
    loader = PhillyOpaLoader(csv_path=sample_csv, county_id=philly_county_id)

    run = run_loader(db_session, loader, batch_size=10)

    assert run.rows_seen == 2
    assert run.rows_inserted == 2
    assert run.rows_unchanged == 0
    assert loader.stats.seen == 4
    assert loader.stats.mapped == 2
    assert loader.stats.skipped_city_owned == 1
    assert loader.stats.skipped_no_market_value == 1


@pytest.mark.integration
def test_loaded_properties_have_correct_fields(db_session, sample_csv, philly_county_id):
    loader = PhillyOpaLoader(csv_path=sample_csv, county_id=philly_county_id)
    run_loader(db_session, loader)

    stmt = select(Property).where(Property.parcel_id == "661127300")
    prop = db_session.scalars(stmt).one()

    assert prop.address_full == "3626 MORRELL AVE"
    assert prop.address_normalized == "3626 morrell ave"
    assert prop.street_number == "3626"
    assert prop.street_name == "MORRELL"
    assert prop.zip_code == "19114"
    assert prop.year_built == 1961
    assert prop.current_assessed_total == 302000
    assert prop.property_category == PropertyCategory.ROWHOUSE
    assert prop.source_id == "philly_opa"
    assert prop.raw_data is not None
    assert prop.raw_data["parcel_number"] == "661127300"


@pytest.mark.integration
def test_idempotent_rerun_marks_unchanged(db_session, sample_csv, philly_county_id):
    loader1 = PhillyOpaLoader(csv_path=sample_csv, county_id=philly_county_id)
    run1 = run_loader(db_session, loader1)

    assert run1.rows_inserted == 2

    loader2 = PhillyOpaLoader(csv_path=sample_csv, county_id=philly_county_id)
    run2 = run_loader(db_session, loader2)

    assert run2.rows_inserted == 0
    assert run2.rows_updated == 0
    assert run2.rows_unchanged == 2


@pytest.mark.integration
def test_changed_data_triggers_update(db_session, sample_csv, philly_county_id, tmp_path):
    loader1 = PhillyOpaLoader(csv_path=sample_csv, county_id=philly_county_id)
    run_loader(db_session, loader1)

    modified_rows = [dict(row) for row in SAMPLE_ROWS]
    modified_rows[0]["market_value"] = "400000"

    modified_csv = tmp_path / "opa_modified.csv"
    fieldnames = list(modified_rows[0].keys())
    with modified_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(modified_rows)

    loader2 = PhillyOpaLoader(csv_path=modified_csv, county_id=philly_county_id)
    run2 = run_loader(db_session, loader2)

    assert run2.rows_updated == 1
    assert run2.rows_unchanged == 1
    assert run2.rows_inserted == 0

    stmt = select(Property).where(Property.parcel_id == "661127300")
    prop = db_session.scalars(stmt).one()
    assert prop.current_assessed_total == 400000


@pytest.mark.integration
def test_trigram_search_works_on_loaded_data(db_session, sample_csv, philly_county_id):
    loader = PhillyOpaLoader(csv_path=sample_csv, county_id=philly_county_id)
    run_loader(db_session, loader)

    result = db_session.execute(
        text("""
            SELECT address_full
            FROM keystone.properties
            WHERE address_normalized % :query
            ORDER BY similarity(address_normalized, :query) DESC
            LIMIT 5
        """),
        {"query": "morrell"},
    ).all()

    addresses = [row[0] for row in result]
    assert any("MORRELL" in addr for addr in addresses)