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
)


class PhillyOpaLoader:
    source_id = "philly_opa"

    def __init__(self, csv_path: Path, county_id: str):
        self.csv_path = csv_path
        self.county_id = county_id
        self.stats = MapStats()

    def fetch(self) -> Iterator[SourceRow]:
        with self.csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mapped = map_row(row, self.county_id, self.stats)
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

        values = [r.payload for r in rows]
        result = UpsertResult()

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
        unchanged_count = len(rows) - written_count

        inserted_count = sum(
            1 for row in written
            if row.created_at == row.updated_at
        )
        updated_count = written_count - inserted_count

        result.inserted = inserted_count
        result.updated = updated_count
        result.unchanged = unchanged_count
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