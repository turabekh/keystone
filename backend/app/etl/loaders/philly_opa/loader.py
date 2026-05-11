import csv
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.etl.loaders.philly_opa.row_mapper import MapStats, map_row
from app.etl.types import SourceRow, UpsertResult
from app.models.county import County
from app.models.property import Property


logger = logging.getLogger(__name__)


_UPSERT_COLUMNS = (
    "address_full",
    "address_normalized",
    "street_number",
    "street_direction",
    "street_name",
    "street_suffix",
    "unit",
    "city",
    "state",
    "zip_code",
    "census_tract",
    "geographic_ward",
    "street_code",
    "property_category",
    "source_property_type",
    "year_built",
    "square_feet_living",
    "square_feet_lot",
    "number_of_bedrooms",
    "number_of_bathrooms",
    "number_of_stories",
    "current_assessed_total",
    "current_assessed_land",
    "current_assessed_building",
    "current_assessment_year",
    "last_sale_date",
    "last_sale_price",
    "source_id",
    "payload_hash",
    "raw_data",
    "hundred_block",
)


POSTGRES_PARAM_LIMIT = 65_535
PARAMS_PER_PROPERTY_ROW = 30
SAFE_BATCH_LIMIT = (POSTGRES_PARAM_LIMIT // PARAMS_PER_PROPERTY_ROW) - 100


class PhillyOpaLoader:
    source_id = "philly_opa"

    def __init__(self, csv_path: Path, county_id: str):
        self.csv_path = csv_path
        self.county_id = county_id
        self.stats = MapStats()

    def fetch(self) -> Iterator[SourceRow]:
        with self.csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for raw_count, row in enumerate(reader, start=1):
                mapped = map_row(row, self.county_id, self.stats)
                if raw_count % 50_000 == 0:
                    logger.info(
                        "csv_progress",
                        extra={
                            "raw_rows_seen": raw_count,
                            "mapped": self.stats.mapped,
                            "skipped_no_market_value": self.stats.skipped_no_market_value,
                            "skipped_city_owned": self.stats.skipped_city_owned,
                            "skipped_no_parcel": self.stats.skipped_no_parcel,
                        },
                    )
                if mapped is None:
                    continue
                yield SourceRow(
                    natural_key=mapped.parcel_id,
                    payload={
                        **mapped.payload,
                        "raw_data": mapped.raw_data,
                    },
                )

    def upsert_batch(self, session: Session, rows: list[SourceRow]) -> UpsertResult:
        if not rows:
            return UpsertResult()

        result = UpsertResult()
        for sub_batch in _split_into_safe_batches(rows):
            result += self._upsert_one(session, sub_batch)
        return result

    def _upsert_one(self, session: Session, rows: list[SourceRow]) -> UpsertResult:
        if not rows:
            return UpsertResult()

        deduped = _deduplicate_by_natural_key(rows)
        if len(deduped) != len(rows):
            logger.info(
                "deduped_batch",
                extra={"original": len(rows), "deduped": len(deduped)},
            )

        values = [r.payload for r in deduped]
        table = Property.__table__

        stmt = insert(table).values(values)
        update_columns = {col: stmt.excluded[col] for col in _UPSERT_COLUMNS}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_properties_county_id_parcel_id",
            set_=update_columns,
            where=table.c.payload_hash != stmt.excluded.payload_hash,
        ).returning(table.c.id, table.c.created_at, table.c.updated_at)

        written = session.execute(stmt).all()
        written_count = len(written)
        unchanged_count = len(deduped) - written_count

        inserted_count = sum(
            1 for row in written
            if row.created_at == row.updated_at
        )
        updated_count = written_count - inserted_count

        return UpsertResult(
            inserted=inserted_count,
            updated=updated_count,
            unchanged=unchanged_count,
        )


def _split_into_safe_batches(rows: list[SourceRow]) -> Iterator[list[SourceRow]]:
    if len(rows) <= SAFE_BATCH_LIMIT:
        yield rows
        return
    for i in range(0, len(rows), SAFE_BATCH_LIMIT):
        yield rows[i:i + SAFE_BATCH_LIMIT]


def _deduplicate_by_natural_key(rows: list[SourceRow]) -> list[SourceRow]:
    seen: set[str] = set()
    result: list[SourceRow] = []
    for row in rows:
        if row.natural_key in seen:
            continue
        seen.add(row.natural_key)
        result.append(row)
    return result


def load_philly_opa(
    session: Session,
    csv_path: Path,
    *,
    county_slug: str = "philadelphia",
    state: str = "PA",
) -> "PhillyOpaLoader":
    stmt = select(County).where(County.slug == county_slug, County.state == state)
    county = session.scalars(stmt).one_or_none()
    if county is None:
        raise ValueError(f"County not found: state={state}, slug={county_slug}")

    return PhillyOpaLoader(csv_path=csv_path, county_id=str(county.id))