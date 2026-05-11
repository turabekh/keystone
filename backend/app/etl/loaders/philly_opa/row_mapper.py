import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from app.etl.hashing import compute_payload_hash
from app.models.property import PropertyCategory
from app.services.property_category_mapper import map_building_code_description


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MappedProperty:
    parcel_id: str
    payload: dict[str, Any]
    payload_hash: str
    raw_data: dict[str, Any]
    skip_reason: str | None = None


@dataclass(slots=True)
class MapStats:
    seen: int = 0
    mapped: int = 0
    skipped_no_parcel: int = 0
    skipped_no_market_value: int = 0
    skipped_city_owned: int = 0
    failed: int = 0
    skipped_details: list[str] = field(default_factory=list)


_CITY_OWNED_INDICATORS = (
    "CITY OF PHILA",
    "CITY OF PHILADELPHIA",
    "REDEVELOPMENT AUTHORITY",
    "PHILADELPHIA HOUSING AUTHORITY",
    "PHILA HOUSING AUTHORITY",
    "PHA ",
    "SCHOOL DISTRICT OF PHILA",
    "COMMONWEALTH OF PA",
    "COMMONWEALTH OF PENNSYLVANIA",
    "UNITED STATES OF AMERICA",
    "UNITED STATES POSTAL",
    "SEPTA",
)


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


def _to_decimal(value: Any) -> Decimal | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _to_date(value: Any) -> date | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    candidates = [
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _is_city_owned(owner_1: str | None, owner_2: str | None) -> bool:
    for owner in (owner_1, owner_2):
        if not owner:
            continue
        upper = owner.upper()
        if any(indicator in upper for indicator in _CITY_OWNED_INDICATORS):
            return True
    return False


def _normalize_address(location: str | None) -> str:
    if not location:
        return ""
    return " ".join(location.lower().split())


def _build_payload(row: dict[str, str], county_id: str) -> dict[str, Any]:
    location = _clean(row.get("location")) or ""
    market_value = _to_int(row.get("market_value"))
    year_built = _to_int(row.get("year_built"))
    if year_built is not None and (year_built < 1600 or year_built > 2100):
        year_built = None

    category = map_building_code_description(
        _clean(row.get("building_code_description")),
        _clean(row.get("category_code_description")),
    )

    bathrooms = _to_decimal(row.get("number_of_bathrooms"))
    stories = _to_decimal(row.get("number_stories"))

    direction = _clean(row.get("street_direction"))
    if direction:
        direction = direction.upper().replace(".", "")

    zip_code = _clean(row.get("zip_code"))
    if zip_code:
        zip_code = zip_code.split("-")[0][:5]
        if not zip_code.isdigit():
            zip_code = None

    sale_price = _to_int(row.get("sale_price"))
    if sale_price is not None and sale_price < 0:
        sale_price = None

    payload: dict[str, Any] = {
        "county_id": county_id,
        "parcel_id": _clean(row.get("parcel_number")),
        "address_full": location,
        "address_normalized": _normalize_address(location),
        "street_number": _clean(row.get("house_number")),
        "street_direction": direction,
        "street_name": _clean(row.get("street_name")),
        "street_suffix": _clean(row.get("street_designation")),
        "unit": _clean(row.get("unit")),
        "city": "PHILADELPHIA",
        "state": "PA",
        "zip_code": zip_code,
        "property_category": category.value,
        "source_property_type": _clean(row.get("building_code_description")),
        "year_built": year_built,
        "square_feet_living": _to_int(row.get("total_livable_area")),
        "square_feet_lot": _to_int(row.get("total_area")),
        "number_of_bedrooms": _to_int(row.get("number_of_bedrooms")),
        "number_of_bathrooms": float(bathrooms) if bathrooms is not None else None,
        "number_of_stories": float(stories) if stories is not None else None,
        "current_assessed_total": market_value,
        "current_assessed_land": _to_int(row.get("taxable_land")),
        "current_assessed_building": _to_int(row.get("taxable_building")),
        "current_assessment_year": _today_assessment_year(),
        "last_sale_date": _to_date(row.get("sale_date")),
        "last_sale_price": sale_price,
        "source_id": "philly_opa",
        "census_tract": _clean(row.get("census_tract")),
        "geographic_ward": _clean(row.get("geographic_ward")),
        "street_code": _clean(row.get("street_code")),
    }

    return payload


def _today_assessment_year() -> int:
    return datetime.now(timezone.utc).year


def map_row(row: dict[str, str], county_id: str, stats: MapStats) -> MappedProperty | None:
    stats.seen += 1

    parcel_id = _clean(row.get("parcel_number"))
    if not parcel_id:
        stats.skipped_no_parcel += 1
        return None

    market_value = _to_int(row.get("market_value"))
    if market_value is None:
        stats.skipped_no_market_value += 1
        return None

    if _is_city_owned(_clean(row.get("owner_1")), _clean(row.get("owner_2"))):
        stats.skipped_city_owned += 1
        return None

    try:
        payload = _build_payload(row, county_id)
    except Exception as exc:
        stats.failed += 1
        logger.warning("Failed to map row for parcel %s: %s", parcel_id, exc)
        return None

    hash_input = {k: v for k, v in payload.items() if k != "county_id"}
    payload_hash = compute_payload_hash(hash_input)
    payload["payload_hash"] = payload_hash

    stats.mapped += 1
    return MappedProperty(
        parcel_id=parcel_id,
        payload=payload,
        payload_hash=payload_hash,
        raw_data=dict(row),
    )