from collections.abc import Iterator

import pytest
from sqlalchemy import select

from app.etl import run_loader
from app.etl.types import SourceRow, UpsertResult
from app.models.etl_run import EtlRun, EtlRunStatus


class StubLoader:
    source_id = "stub_loader"

    def __init__(self, rows: list[SourceRow], fail_on_batch: int | None = None):
        self.rows = rows
        self.fail_on_batch = fail_on_batch
        self.batch_count = 0

    def fetch(self) -> Iterator[SourceRow]:
        yield from self.rows

    def upsert_batch(self, session, rows: list[SourceRow]) -> UpsertResult:
        self.batch_count += 1
        if self.fail_on_batch is not None and self.batch_count == self.fail_on_batch:
            raise RuntimeError("simulated batch failure")
        return UpsertResult(inserted=len(rows), updated=0, unchanged=0, failed=0)


@pytest.mark.integration
def test_runner_creates_run_record(db_session):
    rows = [SourceRow(natural_key=str(i), payload={"n": i}) for i in range(5)]
    loader = StubLoader(rows)

    run = run_loader(db_session, loader, batch_size=10)

    assert run.id is not None
    assert run.status == EtlRunStatus.SUCCESS
    assert run.rows_seen == 5
    assert run.rows_inserted == 5
    assert run.finished_at is not None


@pytest.mark.integration
def test_runner_handles_batches(db_session):
    rows = [SourceRow(natural_key=str(i), payload={"n": i}) for i in range(25)]
    loader = StubLoader(rows)

    run = run_loader(db_session, loader, batch_size=10)

    assert run.rows_seen == 25
    assert run.rows_inserted == 25
    assert loader.batch_count == 3


@pytest.mark.integration
def test_runner_marks_partial_on_batch_failure(db_session):
    rows = [SourceRow(natural_key=str(i), payload={"n": i}) for i in range(30)]
    loader = StubLoader(rows, fail_on_batch=2)

    run = run_loader(db_session, loader, batch_size=10)

    assert run.status == EtlRunStatus.PARTIAL
    assert run.rows_seen == 30
    assert run.rows_inserted == 20
    assert run.rows_failed == 10


@pytest.mark.integration
def test_runner_respects_limit(db_session):
    rows = [SourceRow(natural_key=str(i), payload={"n": i}) for i in range(100)]
    loader = StubLoader(rows)

    run = run_loader(db_session, loader, batch_size=10, limit=15)

    assert run.rows_seen == 15
    assert run.rows_inserted == 15


@pytest.mark.integration
def test_runner_logs_run_in_database(db_session):
    rows = [SourceRow(natural_key=str(i), payload={"n": i}) for i in range(3)]
    loader = StubLoader(rows)

    run = run_loader(db_session, loader)
    run_id = run.id

    stmt = select(EtlRun).where(EtlRun.id == run_id)
    found = db_session.scalars(stmt).one()
    assert found.source_id == "stub_loader"
    assert found.status == EtlRunStatus.SUCCESS