import csv
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.etl.loaders.philly_rtt.row_mapper import MapStats, MappedSale, map_row
from app.etl.types import SourceRow, UpsertResult
from app.models.county import County
from app.models.property import Property
from app.models.sale import Sale


logger = logging.getLogger(__name__)


_UPSERT_COLUMNS = (
    "property_id",
    "sale_date",
    "sale_price",
    "deed_type",
    "grantor",
    "grantee",
    "is_arms_length",
    "payload_hash",
    "raw_data",
)


POSTGRES_PARAM_LIMIT = 65_535
PARAMS_PER_SALE_ROW = 12
SAFE_BATCH_LIMIT = (POSTGRES_PARAM_LIMIT // PARAMS_PER_SALE_ROW) - 100


class PhillyRttLoader:
    source_id = "philly_rtt"

    def __init__(self, csv_path: Path, county_id: str):
        self.csv_path = csv_path
        self.county_id = county_id
        self.stats = MapStats()
        self._parcel_to_property_id: dict[str, UUID] | None = None
        self._orphans_logged = 0
        self._orphan_count = 0

    def _load_parcel_index(self, session: Session) -> dict[str, UUID]:
        if self._parcel_to_property_id is not None:
            return self._parcel_to_property_id
        stmt = (
            select(Property.parcel_id, Property.id)
            .where(Property.county_id == self.county_id)
        )
        rows = session.execute(stmt).all()
        self._parcel_to_property_id = {parcel_id: pid for parcel_id, pid in rows}
        logger.info("Loaded parcel index: %d properties", len(self._parcel_to_property_id))
        return self._parcel_to_property_id

    def fetch(self) -> Iterator[SourceRow]:
        with self.csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for raw_count, row in enumerate(reader, start=1):
                mapped = map_row(row, self.stats)
                if raw_count % 50_000 == 0:
                    logger.info(
                        "rtt_csv_progress raw=%d mapped=%d low=%d overlap=%d",
                        raw_count,
                        self.stats.mapped,
                        self.stats.flagged_low_consideration,
                        self.stats.flagged_name_overlap,
                    )
                if mapped is None:
                    continue
                yield SourceRow(
                    natural_key=mapped.document_id,
                    payload={
                        "parcel_id": mapped.parcel_id,
                        "raw_data": mapped.raw_data,
                        **mapped.payload,
                    },
                )

    def upsert_batch(self, session: Session, rows: list[SourceRow]) -> UpsertResult:
        if not rows:
            return UpsertResult()

        parcel_index = self._load_parcel_index(session)

        prepared: list[dict[str, Any]] = []
        for r in rows:
            parcel_id = r.payload["parcel_id"]
            property_id = parcel_index.get(parcel_id)
            if property_id is None:
                self._orphan_count += 1
                if self._orphans_logged < 50:
                    logger.info(
                        "rtt_orphan_skipped parcel=%s document=%s",
                        parcel_id,
                        r.natural_key,
                    )
                    self._orphans_logged += 1
                continue
            payload = {k: v for k, v in r.payload.items() if k != "parcel_id"}
            payload["property_id"] = property_id
            payload["source_id"] = self.source_id
            prepared.append(payload)

        if not prepared:
            return UpsertResult()

        result = UpsertResult()
        for sub_batch in _split_into_safe_batches(prepared):
            result += self._upsert_one(session, sub_batch)
        return result

    def _upsert_one(self, session: Session, rows: list[dict[str, Any]]) -> UpsertResult:
        if not rows:
            return UpsertResult()

        deduped = _deduplicate_by_document_id(rows)
        if len(deduped) != len(rows):
            logger.info(
                "rtt_deduped_batch original=%d deduped=%d",
                len(rows),
                len(deduped),
            )

        table = Sale.__table__
        stmt = insert(table).values(deduped)
        update_columns = {col: stmt.excluded[col] for col in _UPSERT_COLUMNS}
        stmt = stmt.on_conflict_do_update(
            index_elements=[table.c.source_id, table.c.document_number],
            index_where=table.c.document_number.isnot(None),
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


def _split_into_safe_batches(rows: list[Any]) -> Iterator[list[Any]]:
    if len(rows) <= SAFE_BATCH_LIMIT:
        yield rows
        return
    for i in range(0, len(rows), SAFE_BATCH_LIMIT):
        yield rows[i:i + SAFE_BATCH_LIMIT]


def _deduplicate_by_document_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        doc_id = row["document_number"]
        if doc_id in seen:
            continue
        seen.add(doc_id)
        result.append(row)
    return result


def load_philly_rtt(
    session: Session,
    csv_path: Path,
    *,
    county_slug: str = "philadelphia",
    state: str = "PA",
) -> "PhillyRttLoader":
    stmt = select(County).where(County.slug == county_slug, County.state == state)
    county = session.scalars(stmt).one_or_none()
    if county is None:
        raise ValueError(f"County not found: state={state}, slug={county_slug}")

    return PhillyRttLoader(csv_path=csv_path, county_id=str(county.id))