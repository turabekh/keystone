import re
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

import usaddress


US_STATES = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
})


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class ParsedAddress:
    raw: str
    normalized: str
    street_number: str | None = None
    street_direction: str | None = None
    street_name: str | None = None
    street_suffix: str | None = None
    unit: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    confidence: Confidence = Confidence.LOW
    is_parseable: bool = False
    unparsed_tokens: tuple[str, ...] = field(default_factory=tuple)


_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[,\s]+$")
_UNIT_FALLBACK_RE = re.compile(r"\s+(\d+[A-Za-z])\s*$")
_UNIT_PREFIX_RE = re.compile(r"^(#\s*|apt\.?\s+|unit\s+|ste\.?\s+|suite\s+)", re.IGNORECASE)

def _clean_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    cleaned = _UNIT_PREFIX_RE.sub("", unit).strip()
    return cleaned or None



def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = _WHITESPACE_RE.sub(" ", s)
    return s


def _clean_token(token: str) -> str:
    return _TRAILING_PUNCT_RE.sub("", token).strip()


def _score_confidence(parsed: dict[str, str], address_type: str) -> Confidence:
    has_number = bool(parsed.get("AddressNumber"))
    has_street = bool(parsed.get("StreetName"))
    has_state = bool(parsed.get("StateName"))
    has_zip = bool(parsed.get("ZipCode"))
    has_city = bool(parsed.get("PlaceName"))

    if address_type != "Street Address":
        return Confidence.LOW

    if has_number and has_street and has_state and has_zip:
        return Confidence.HIGH

    if has_number and has_street and (has_state or has_zip or has_city):
        return Confidence.MEDIUM

    if has_number and has_street:
        return Confidence.MEDIUM

    return Confidence.LOW


def _extract_unit_fallback(raw: str, current_unit: str | None) -> str | None:
    if current_unit:
        return current_unit
    match = _UNIT_FALLBACK_RE.search(raw)
    if match:
        return match.group(1)
    return None


@lru_cache(maxsize=10_000)
def parse(raw: str) -> ParsedAddress:
    if not raw or not raw.strip():
        return ParsedAddress(raw=raw or "", normalized="", is_parseable=False)

    normalized = _normalize(raw)

    try:
        tagged, address_type = usaddress.tag(raw)
    except usaddress.RepeatedLabelError as exc:
        return ParsedAddress(
            raw=raw,
            normalized=normalized,
            is_parseable=False,
            unparsed_tokens=tuple(token for token, _ in exc.parsed_string),
        )

    parsed = {k: _clean_token(v) for k, v in tagged.items()}

    state = parsed.get("StateName")
    if state:
        state = state.upper()
        if state not in US_STATES:
            state = None

    zip_code = parsed.get("ZipCode")
    if zip_code:
        zip_code = zip_code.split("-")[0][:5]
        if not zip_code.isdigit() or len(zip_code) != 5:
            zip_code = None

    direction = parsed.get("StreetNamePreDirectional") or parsed.get("StreetNamePostDirectional")
    if direction:
        direction = direction.upper().replace(".", "")

    street_number = parsed.get("AddressNumber")
    street_name = parsed.get("StreetName")
    street_suffix = parsed.get("StreetNamePostType")
    unit = _clean_unit(parsed.get("OccupancyIdentifier"))
    city = parsed.get("PlaceName")

    unit = _extract_unit_fallback(raw, unit)

    is_parseable = (
        address_type == "Street Address"
        and bool(street_number)
        and bool(street_name)
    )

    confidence = _score_confidence(parsed, address_type)

    return ParsedAddress(
        raw=raw,
        normalized=normalized,
        street_number=street_number,
        street_direction=direction,
        street_name=street_name,
        street_suffix=street_suffix,
        unit=unit,
        city=city,
        state=state,
        zip_code=zip_code,
        confidence=confidence,
        is_parseable=is_parseable,
    )