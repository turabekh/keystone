import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from itertools import islice
from typing import Any

from sqlalchemy.orm import Session

from app.etl.types import Loader, SourceRow, UpsertResult
from app.models.etl_run import EtlRun, EtlRunStatus


logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 1000


@contextmanager
def loader_run(session: Session, source_id: str, metadata: dict[str, Any] | None = None):
    run = EtlRun(source_id=source_id, status=EtlRunStatus.RUNNING, source_metadata=metadata)
    session.add(run)
    session.commit()
    session.refresh(run)

    try:
        yield run
    except Exception as exc:
        run.status = EtlRunStatus.FAILED
        run.error_message = str(exc)[:5000]
        run.finished_at = datetime.now(UTC)
        session.commit()
        raise
    else:
        if run.status == EtlRunStatus.RUNNING:
            run.status = EtlRunStatus.SUCCESS if run.rows_failed == 0 else EtlRunStatus.PARTIAL
        run.finished_at = datetime.now(UTC)
        session.commit()


def batched(iterator: Iterator[SourceRow], size: int) -> Iterator[list[SourceRow]]:
    it = iter(iterator)
    while batch := list(islice(it, size)):
        yield batch


def run_loader(
    session: Session,
    loader: Loader,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    limit: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> EtlRun:
    with loader_run(session, loader.source_id, metadata) as run:
        rows_iter = loader.fetch()
        if limit is not None:
            rows_iter = islice(rows_iter, limit)

        total = UpsertResult()

        for batch in batched(rows_iter, batch_size):
            batch_len = len(batch)
            try:
                result = loader.upsert_batch(session, batch)
                total += result
                session.commit()
            except Exception:
                session.rollback()
                total.failed += batch_len
                logger.exception("Batch failed in loader %s", loader.source_id)

            run.rows_seen += batch_len
            run.rows_inserted = total.inserted
            run.rows_updated = total.updated
            run.rows_unchanged = total.unchanged
            run.rows_failed = total.failed
            session.commit()

        return run