import pytest

from app.etl.loaders.philly_rtt.row_mapper import (
    MapStats,
    _clean,
    _looks_like_entity,
    _names_overlap,
    _to_date,
    _to_int,
    map_row,
)
from datetime import date


def _sample_row(**overrides):
    base = {
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
    }
    base.update(overrides)
    return base


def test_to_int_handles_real_consideration():
    assert _to_int("251000") == 251000
    assert _to_int("1") == 1
    assert _to_int("") is None
    assert _to_int(None) is None


def test_to_date_iso_with_z():
    assert _to_date("2026-02-27T10:00:00Z") == date(2026, 2, 27)


def test_to_date_iso_with_offset():
    assert _to_date("2026-03-18T02:16:17Z") == date(2026, 3, 18)


def test_to_date_invalid():
    assert _to_date("garbage") is None
    assert _to_date("") is None


def test_names_overlap_intrafamily():
    assert _names_overlap("MONTAGUE LINDA A;WILLIAMS LINDA A", "MONTAGUE WARREN S") is True


def test_names_overlap_arms_length():
    assert _names_overlap("TROIA STEFANIO G", "UNG GUOLAN;LIN CHENGYAO") is False


def test_names_overlap_handles_empty():
    assert _names_overlap(None, "SMITH JOHN") is False
    assert _names_overlap("SMITH JOHN", None) is False
    assert _names_overlap("", "") is False


def test_map_row_arms_length_sale():
    stats = MapStats()
    result = map_row(_sample_row(), stats)
    assert result is not None
    assert result.parcel_id == "141463300"
    assert result.document_id == "54530625"
    assert result.payload["sale_price"] == 251000
    assert result.payload["sale_date"] == date(2026, 2, 27)
    assert result.payload["deed_type"] == "DEED"
    assert result.payload["is_arms_length"] is True
    assert stats.mapped == 1


def test_map_row_intrafamily_flagged():
    row = _sample_row(
        total_consideration="1",
        cash_consideration="1",
        grantors="WILLIAMS LINDA A;MONTAGUE LINDA A",
        grantees="MONTAGUE LINDA A;MONTAGUE WARREN S",
    )
    stats = MapStats()
    result = map_row(row, stats)
    assert result is not None
    assert result.payload["is_arms_length"] is False
    assert stats.flagged_low_consideration == 1


def test_map_row_name_overlap_flagged():
    row = _sample_row(
        total_consideration="200000",
        grantors="SMITH JOHN",
        grantees="SMITH JANE",
    )
    stats = MapStats()
    result = map_row(row, stats)
    assert result is not None
    assert result.payload["is_arms_length"] is False
    assert stats.flagged_name_overlap == 1


def test_map_row_skips_no_parcel():
    row = _sample_row(opa_account_num="")
    stats = MapStats()
    result = map_row(row, stats)
    assert result is None
    assert stats.skipped_no_parcel == 1


def test_map_row_skips_no_date():
    row = _sample_row(display_date="")
    stats = MapStats()
    result = map_row(row, stats)
    assert result is None
    assert stats.skipped_no_date == 1


def test_map_row_skips_no_document_id():
    row = _sample_row(document_id="")
    stats = MapStats()
    result = map_row(row, stats)
    assert result is None
    assert stats.skipped_bad_document_id == 1


def test_map_row_falls_back_to_cash_consideration():
    row = _sample_row(total_consideration="", cash_consideration="300000")
    stats = MapStats()
    result = map_row(row, stats)
    assert result is not None
    assert result.payload["sale_price"] == 300000


def test_map_row_skips_no_consideration_at_all():
    row = _sample_row(total_consideration="", cash_consideration="")
    stats = MapStats()
    result = map_row(row, stats)
    assert result is None
    assert stats.skipped_no_consideration == 1


def test_hash_is_stable():
    row = _sample_row()
    r1 = map_row(row, MapStats())
    r2 = map_row(row, MapStats())
    assert r1.payload_hash == r2.payload_hash


def test_hash_changes_on_price_change():
    r1 = map_row(_sample_row(total_consideration="200000"), MapStats())
    r2 = map_row(_sample_row(total_consideration="300000"), MapStats())
    assert r1.payload_hash != r2.payload_hash


def test_raw_data_preserved():
    row = _sample_row()
    row["objectid"] = "999"
    result = map_row(row, MapStats())
    assert result.raw_data["objectid"] == "999"


def test_to_date_handles_carto_csv_timestamptz_format():
    assert _to_date("2026-01-01 00:14:56+00") == date(2026, 1, 1)
    assert _to_date("2026-03-13 08:00:00+00") == date(2026, 3, 13)


def test_to_date_handles_negative_offset():
    assert _to_date("2026-03-06 00:00:00-05") == date(2026, 3, 6)


def test_to_date_handles_full_offset():
    assert _to_date("2026-03-06 00:00:00-0500") == date(2026, 3, 6)


def test_all_seen_rows_accounted_for():
    """Every row that increments `seen` must increment exactly one outcome counter."""
    rows = [
        {"opa_account_num": "", "document_id": "1", "display_date": "2026-01-01 00:00:00+00",
         "total_consideration": "100000", "cash_consideration": "100000",
         "grantors": "A", "grantees": "B", "document_type": "DEED"},
        {"opa_account_num": "123", "document_id": "", "display_date": "2026-01-01 00:00:00+00",
         "total_consideration": "100000", "cash_consideration": "100000",
         "grantors": "A", "grantees": "B", "document_type": "DEED"},
        {"opa_account_num": "123", "document_id": "1", "display_date": "",
         "total_consideration": "100000", "cash_consideration": "100000",
         "grantors": "A", "grantees": "B", "document_type": "DEED"},
        {"opa_account_num": "123", "document_id": "2", "display_date": "2026-01-01 00:00:00+00",
         "total_consideration": "", "cash_consideration": "",
         "grantors": "A", "grantees": "B", "document_type": "DEED"},
        {"opa_account_num": "123", "document_id": "3", "display_date": "2026-01-01 00:00:00+00",
         "total_consideration": "100000", "cash_consideration": "100000",
         "grantors": "A", "grantees": "B", "document_type": "DEED"},
    ]
    stats = MapStats()
    for row in rows:
        map_row(row, stats)
    accounted = (
        stats.mapped
        + stats.skipped_no_parcel
        + stats.skipped_bad_document_id
        + stats.skipped_no_date
        + stats.skipped_no_consideration
        + stats.failed
    )
    assert accounted == stats.seen, (
        f"Lost rows: seen={stats.seen}, accounted={accounted}, "
        f"stats={stats}"
    )

def test_names_overlap_entity_to_entity_not_flagged():
    """LLC-to-LLC transfers with same place-name should not be flagged."""
    assert _names_overlap("MELROSE PARK MANOR ASSOCIATES", "MELROSE PARK APTS LLC") is False
    assert _names_overlap("BIRCHWOOD APARTMENTS LP", "BIRCHWOOD HILL APTS LLC") is False
    assert _names_overlap("1432 PARTNERS LIMITED LIABILITY COMPANY", "1432 NORTH BROAD LLC") is False


def test_names_overlap_entity_to_person_not_flagged():
    """Entity-to-person transfers (or vice versa) should not be flagged on surname overlap alone
    when the entity is a clearly-corporate type. Family trusts are an exception — they're
    typically wealth-planning vehicles for the same family, so we want overlap to fire."""
    assert _names_overlap("TEMPLE U INVESTMENT GROUP LLC", "TEMPLE UNIVERSITY") is False
    assert _names_overlap("SMITH JOHN", "ACME PROPERTIES LLC") is False


def test_names_overlap_real_intrafamily_still_caught():
    """The Wright-family case from real data should still be flagged."""
    assert _names_overlap(
        "SOLOMAN HOWARD M;WRIGHT ALETHIA C ESTATE OF",
        "WRIGHT EDWARD C;WRIGHT NINA",
    ) is True


def test_names_overlap_two_personal_names_with_same_surname():
    assert _names_overlap("MONTAGUE LINDA A", "MONTAGUE WARREN S") is True
    assert _names_overlap("SMITH JOHN;JONES MARY", "SMITH JANE") is True


def test_looks_like_entity():
    assert _looks_like_entity("ACME LLC") is True
    assert _looks_like_entity("PHILADELPHIA PARKING AUTHORITY") is True
    assert _looks_like_entity("TEMPLE UNIVERSITY") is True
    assert _looks_like_entity("MELROSE PARK MANOR ASSOCIATES") is True
    assert _looks_like_entity("SMITH JOHN A") is False
    assert _looks_like_entity("WRIGHT EDWARD C") is False
    assert _looks_like_entity("SMITH FAMILY TRUST") is False
    assert _looks_like_entity("WRIGHT ALETHIA C ESTATE OF") is False

def test_names_overlap_estate_transfer_still_caught():
    """'ESTATE OF' is family-context language, not an entity marker."""
    assert _names_overlap("WRIGHT ALETHIA C ESTATE OF", "WRIGHT EDWARD C") is True
    assert _names_overlap("SMITH JOHN ESTATE OF", "SMITH JANE") is True


def test_names_overlap_personal_trust_still_caught():
    """Personal trusts where surnames match should still be flagged."""
    assert _names_overlap("SMITH JOHN TRUSTEES OF SMITH FAMILY", "SMITH JANE") is True


def test_looks_like_entity_does_not_flag_estate_or_trustees():
    assert _looks_like_entity("WRIGHT ALETHIA C ESTATE OF") is False
    assert _looks_like_entity("SMITH JOHN TRUSTEES OF") is False


def test_looks_like_entity_still_flags_real_entities():
    assert _looks_like_entity("MELROSE PARK MANOR ASSOCIATES") is True
    assert _looks_like_entity("ACME LLC") is True
    assert _looks_like_entity("TEMPLE UNIVERSITY") is True
    assert _looks_like_entity("PHILADELPHIA PARKING AUTHORITY") is True