import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.etl.hashing import compute_payload_hash


logger = logging.getLogger(__name__)

MIN_ARMS_LENGTH_CONSIDERATION = 1000


@dataclass(slots=True)
class MappedSale:
    parcel_id: str
    document_id: str
    payload: dict[str, Any]
    payload_hash: str
    raw_data: dict[str, Any]


@dataclass(slots=True)
class MapStats:
    seen: int = 0
    mapped: int = 0
    skipped_no_parcel: int = 0
    skipped_no_date: int = 0
    skipped_no_consideration: int = 0
    skipped_bad_document_id: int = 0
    flagged_low_consideration: int = 0
    flagged_name_overlap: int = 0
    failed: int = 0


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() in {"NULL", "NONE", "N/A"}:
        return None
    return s


def _to_int(value: Any) -> int | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return int(Decimal(cleaned))
    except (InvalidOperation, ValueError):
        return None


def _to_date(value: Any) -> date | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    candidates = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    normalized = cleaned
    if len(normalized) >= 22 and normalized[-3] == "+" and normalized[-2:].isdigit():
        normalized = normalized + "00"
    elif len(normalized) >= 22 and normalized[-3] == "-" and normalized[-2:].isdigit():
        normalized = normalized + "00"
    for fmt in candidates:
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(cleaned.replace(" ", "T")).date()
    except ValueError:
        return None


def _split_parties(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(";") if p.strip()]



_ENTITY_TOKENS = frozenset({
    "LLC", "LP", "LLP", "INC", "CORP", "CORPORATION", "COMPANY", "CO",
    "ASSOCIATES", "ASSOCIATION", "PARTNERS", "PARTNERSHIP",
    "GROUP", "FUND", "HOLDINGS", "PROPERTIES", "PROPERTY",
    "INVESTMENTS", "INVESTMENT", "REALTY", "DEVELOPMENT",
    "AUTHORITY", "AGENCY", "COMMONWEALTH", "FOUNDATION", "BANK", "FEDERAL",
    "ASSN", "MGMT", "MANAGEMENT", "ENTERPRISES", "VENTURES", "CAPITAL",
    "UNIVERSITY", "SCHOOL", "CHURCH",
})

def _looks_like_entity(party: str) -> bool:
    tokens = party.upper().split()
    return any(tok.rstrip(",.") in _ENTITY_TOKENS for tok in tokens)


def _any_party_is_entity(parties: list[str]) -> bool:
    return any(_looks_like_entity(p) for p in parties)


def _last_names(parties: list[str]) -> set[str]:
    result: set[str] = set()
    for p in parties:
        first_token = p.split()[0] if p else ""
        if first_token:
            result.add(first_token.upper())
    return result


def _names_overlap(grantors: str | None, grantees: str | None) -> bool:
    grantor_parties = _split_parties(grantors)
    grantee_parties = _split_parties(grantees)
    if not grantor_parties or not grantee_parties:
        return False
    if _any_party_is_entity(grantor_parties) or _any_party_is_entity(grantee_parties):
        return False
    g1 = _last_names(grantor_parties)
    g2 = _last_names(grantee_parties)
    if not g1 or not g2:
        return False
    return bool(g1 & g2)


def _compute_is_arms_length(
    consideration: int | None,
    grantors: str | None,
    grantees: str | None,
    stats: MapStats,
) -> bool:
    if consideration is None or consideration < MIN_ARMS_LENGTH_CONSIDERATION:
        stats.flagged_low_consideration += 1
        return False
    if _names_overlap(grantors, grantees):
        stats.flagged_name_overlap += 1
        return False
    return True


def map_row(row: dict[str, str], stats: MapStats) -> MappedSale | None:
    stats.seen += 1

    parcel_id = _clean(row.get("opa_account_num"))
    if not parcel_id:
        stats.skipped_no_parcel += 1
        return None

    document_id = _clean(row.get("document_id"))
    if not document_id:
        stats.skipped_bad_document_id += 1
        return None

    sale_date = _to_date(row.get("display_date"))
    if sale_date is None:
        stats.skipped_no_date += 1
        return None

    consideration = _to_int(row.get("total_consideration"))
    if consideration is None:
        consideration = _to_int(row.get("cash_consideration"))
    if consideration is None:
        stats.skipped_no_consideration += 1
        return None

    if consideration < 0:
        consideration = 0

    grantors = _clean(row.get("grantors"))
    grantees = _clean(row.get("grantees"))

    is_arms_length = _compute_is_arms_length(consideration, grantors, grantees, stats)

    try:
        payload: dict[str, Any] = {
            "sale_date": sale_date,
            "sale_price": consideration,
            "document_number": document_id,
            "deed_type": _clean(row.get("document_type")),
            "grantor": grantors,
            "grantee": grantees,
            "is_arms_length": is_arms_length,
            "source_id": "philly_rtt",
        }
    except Exception as exc:
        stats.failed += 1
        logger.warning("Failed to map RTT row %s: %s", document_id, exc)
        return None

    hash_input = {k: v for k, v in payload.items() if k != "source_id"}
    payload_hash = compute_payload_hash(hash_input)
    payload["payload_hash"] = payload_hash

    stats.mapped += 1
    return MappedSale(
        parcel_id=parcel_id,
        document_id=document_id,
        payload=payload,
        payload_hash=payload_hash,
        raw_data=dict(row),
    )