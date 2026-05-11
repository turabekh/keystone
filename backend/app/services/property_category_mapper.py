from app.models.property import PropertyCategory


_ROWHOUSE_PREFIXES = (
    "ROW ",
    "ROW/",
    "ROW-",
)

_TWIN_PREFIXES = (
    "TWIN",
    "SEMI/DET",
    "SEMI-DET",
    "SEMI DET",
    "S/D",
)

_DET_PREFIXES = (
    "DET ",
    "DETACHED",
    "SINGLE FAMILY DETACHED",
)

_MULTI_FAMILY_KEYWORDS = (
    "APT",
    "APARTMENT",
    "CONV APT",
    "MULTI",
    "DUPLEX",
    "TRIPLEX",
    "QUADPLEX",
    "ROOMING",
)

_CONDO_KEYWORDS = (
    "CONDO",
    "CONDOMINIUM",
)

_MIXED_USE_KEYWORDS = (
    "STR/APT",
    "STR/OFF",
    "STORE/APT",
    "STORE/OFF",
    "STR W/APT",
    "MIXED USE",
    "MIXED-USE",
)

_COMMERCIAL_KEYWORDS = (
    "OFF BLD",
    "OFF BUILDING",
    "STORE",
    "OFFICE",
    "WAREHOUSE",
    "FACTORY",
    "INDUSTRIAL",
    "COMMERCIAL",
    "RETAIL",
    "RESTAURANT",
    "REST'RNT",
    "HOTEL",
    "MOTEL",
    "GAS STATION",
    "GARAGE COMMERCIAL",
    "AUTO",
    "BANK",
    "SHOPPING",
    "SCHOOL",
    "HEALTH FAC",
    "HOSPITAL",
    "CLINIC",
    "PUB UTIL",
    "AMUSE",
)

_VACANT_KEYWORDS = (
    "VACANT",
    "LOT",
)


def map_building_code_description(description: str | None, category_description: str | None = None) -> PropertyCategory:
    if not description:
        return _map_from_category(category_description)

    normalized = description.upper().strip()

    if any(kw in normalized for kw in _MIXED_USE_KEYWORDS):
        return PropertyCategory.MIXED_USE

    if any(kw in normalized for kw in _CONDO_KEYWORDS):
        return PropertyCategory.CONDO

    if normalized.startswith(_ROWHOUSE_PREFIXES):
        if any(kw in normalized for kw in _MULTI_FAMILY_KEYWORDS):
            return PropertyCategory.MULTI_FAMILY
        return PropertyCategory.ROWHOUSE

    if any(normalized.startswith(p) for p in _TWIN_PREFIXES):
        if any(kw in normalized for kw in _MULTI_FAMILY_KEYWORDS):
            return PropertyCategory.MULTI_FAMILY
        return PropertyCategory.TWIN_SEMI

    if any(p in normalized for p in _DET_PREFIXES):
        if any(kw in normalized for kw in _MULTI_FAMILY_KEYWORDS):
            return PropertyCategory.MULTI_FAMILY
        return PropertyCategory.SINGLE_FAMILY

    if any(kw in normalized for kw in _MULTI_FAMILY_KEYWORDS):
        return PropertyCategory.MULTI_FAMILY

    if any(kw in normalized for kw in _COMMERCIAL_KEYWORDS):
        return PropertyCategory.COMMERCIAL

    if any(kw in normalized for kw in _VACANT_KEYWORDS):
        return PropertyCategory.VACANT

    return _map_from_category(category_description)


def _map_from_category(category_description: str | None) -> PropertyCategory:
    if not category_description:
        return PropertyCategory.OTHER

    normalized = category_description.upper().strip()

    if "SINGLE FAMILY" in normalized:
        return PropertyCategory.SINGLE_FAMILY
    if "MULTI" in normalized or "APT" in normalized or "APARTMENT" in normalized:
        return PropertyCategory.MULTI_FAMILY
    if "CONDO" in normalized:
        return PropertyCategory.CONDO
    if "COMMERCIAL" in normalized:
        return PropertyCategory.COMMERCIAL
    if "VACANT" in normalized:
        return PropertyCategory.VACANT
    if "INDUSTRIAL" in normalized:
        return PropertyCategory.COMMERCIAL
    if "MIXED" in normalized:
        return PropertyCategory.MIXED_USE

    return PropertyCategory.OTHER