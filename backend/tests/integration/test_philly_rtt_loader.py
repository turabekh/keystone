import csv
from pathlib import Path

import pytest
from sqlalchemy import select

from app.etl import run_loader
from app.etl.loaders.philly_rtt.loader import PhillyRttLoader, load_philly_rtt
from app.models.county import County
from app.models.property import Property
from app.models.sale import Sale


SAMPLE_RTT_ROWS = [
    {
        "document_id": "54530625",
        "document_type": "DEED",
        "opa_account_num": "141463300",
        "display_date": "2026-02-27T10:00:00Z",
        "total_consideration": "251000",
        "cash_consideration": "251000",
        "adjusted_total_consideration": "251000",
        "grantors": "TROIA STEFANIO G;POTTS MILDRED P ESTATE OF",
        "grantees": "UNG GUOLAN;LIN CHENGYAO",
        "street_address": "1204 MASTER ST",
        "legal_remarks": "",
        "discrepancy": "False",
    },
    {
        "document_id": "54530667",
        "document_type": "DEED",
        "opa_account_num": "403245200",
        "display_date": "2026-03-03T10:00:00Z",
        "total_consideration": "1",
        "cash_consideration": "1",
        "adjusted_total_consideration": "1",
        "grantors": "WILLIAMS LINDA A;MONTAGUE LINDA A",
        "grantees": "MONTAGUE LINDA A;MONTAGUE WARREN S",
        "street_address": "6843 REGENT ST",
        "legal_remarks": "",
        "discrepancy": "False",
    },
    {
        "document_id": "99999999",
        "document_type": "DEED",
        "opa_account_num": "000000000",
        "display_date": "2026-03-15T10:00:00Z",
        "total_consideration": "400000",
        "cash_consideration": "400000",
        "adjusted_total_consideration": "400000",
        "grantors": "ORPHAN SELLER LLC",
        "grantees": "ORPHAN BUYER LLC",
        "street_address": "1 NOWHERE ST",
        "legal_remarks": "",
        "discrepancy": "False",
    },
]


@pytest.fixture
def sample_rtt_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "rtt_sample.csv"
    fieldnames = list(SAMPLE_RTT_ROWS[0].keys())
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(SAMPLE_RTT_ROWS)
    return csv_path


@pytest.fixture
def philly_county_id(db_session) -> str:
    stmt = select(County).where(County.slug == "philadelphia", County.state == "PA")
    county = db_session.scalars(stmt).one()
    return str(county.id)


@pytest.mark.integration
def test_loader_resolves_county(db_session, sample_rtt_csv):
    loader = load_philly_rtt(db_session, sample_rtt_csv)
    assert loader.source_id == "philly_rtt"
    assert loader.county_id is not None


@pytest.mark.integration
def test_loader_raises_on_missing_county(db_session, sample_rtt_csv):
    with pytest.raises(ValueError, match="County not found"):
        load_philly_rtt(db_session, sample_rtt_csv, county_slug="nonexistent")


@pytest.mark.integration
def test_loader_inserts_matched_sales_and_skips_orphans(db_session, sample_rtt_csv, philly_county_id, clean_sales):
    loader = PhillyRttLoader(csv_path=sample_rtt_csv, county_id=philly_county_id)
    run = run_loader(db_session, loader, batch_size=10)

    assert loader.stats.seen == 3
    assert loader.stats.mapped == 3
    assert run.rows_inserted == 2
    assert loader._orphan_count == 1


@pytest.mark.integration
def test_loaded_sale_has_correct_fields(db_session, sample_rtt_csv, philly_county_id, clean_sales):
    loader = PhillyRttLoader(csv_path=sample_rtt_csv, county_id=philly_county_id)
    run_loader(db_session, loader)

    stmt = select(Sale).where(Sale.document_number == "54530625")
    sale = db_session.scalars(stmt).one()

    assert sale.sale_price == 251000
    assert sale.deed_type == "DEED"
    assert sale.is_arms_length is True
    assert "TROIA" in sale.grantor
    assert "UNG" in sale.grantee
    assert sale.source_id == "philly_rtt"
    assert sale.raw_data is not None
    assert sale.raw_data["opa_account_num"] == "141463300"


@pytest.mark.integration
def test_intrafamily_sale_flagged_not_arms_length(db_session, sample_rtt_csv, philly_county_id, clean_sales):
    loader = PhillyRttLoader(csv_path=sample_rtt_csv, county_id=philly_county_id)
    run_loader(db_session, loader)

    stmt = select(Sale).where(Sale.document_number == "54530667")
    sale = db_session.scalars(stmt).one()

    assert sale.is_arms_length is False
    assert sale.sale_price == 1


@pytest.mark.integration
def test_idempotent_rerun_marks_unchanged(db_session, sample_rtt_csv, philly_county_id, clean_sales):
    loader1 = PhillyRttLoader(csv_path=sample_rtt_csv, county_id=philly_county_id)
    run1 = run_loader(db_session, loader1)
    assert run1.rows_inserted == 2

    loader2 = PhillyRttLoader(csv_path=sample_rtt_csv, county_id=philly_county_id)
    run2 = run_loader(db_session, loader2)
    assert run2.rows_inserted == 0
    assert run2.rows_updated == 0
    assert run2.rows_unchanged == 2


@pytest.mark.integration
def test_changed_price_triggers_update(db_session, sample_rtt_csv, philly_county_id, tmp_path, clean_sales):
    loader1 = PhillyRttLoader(csv_path=sample_rtt_csv, county_id=philly_county_id)
    run_loader(db_session, loader1)

    modified_rows = [dict(r) for r in SAMPLE_RTT_ROWS]
    modified_rows[0]["total_consideration"] = "275000"
    modified_rows[0]["cash_consideration"] = "275000"

    modified_csv = tmp_path / "rtt_modified.csv"
    fieldnames = list(modified_rows[0].keys())
    with modified_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(modified_rows)

    loader2 = PhillyRttLoader(csv_path=modified_csv, county_id=philly_county_id)
    run2 = run_loader(db_session, loader2)
    assert run2.rows_updated == 1
    assert run2.rows_unchanged == 1

    stmt = select(Sale).where(Sale.document_number == "54530625")
    sale = db_session.scalars(stmt).one()
    assert sale.sale_price == 275000