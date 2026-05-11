import sys
from pathlib import Path

import click

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging, get_logger
from app.etl import run_loader
from app.etl.loaders.philly_opa.downloader import download_opa_csv
from app.etl.loaders.philly_opa.loader import load_philly_opa
from app.etl.loaders.philly_rtt.downloader import download_rtt_csv
from app.etl.loaders.philly_rtt.loader import load_philly_rtt


@click.group()
@click.option("--log-level", default=None, help="Override log level (DEBUG, INFO, WARNING, ERROR)")
def cli(log_level: str | None) -> None:
    if log_level:
        import os
        os.environ["LOG_LEVEL"] = log_level
        get_settings.cache_clear()
    configure_logging()


@cli.command("load-philly-opa")
@click.option("--limit", type=int, default=None, help="Stop after N source rows")
@click.option("--batch-size", type=int, default=1000, help="Rows per upsert batch")
@click.option("--force-download", is_flag=True, help="Redownload CSV even if cached")
@click.option("--csv-path", type=click.Path(exists=True, path_type=Path), default=None, help="Use a specific CSV file instead of downloading")
@click.option("--dry-run", is_flag=True, help="Skip the database write step")
def load_philly_opa_cmd(
    limit: int | None,
    batch_size: int,
    force_download: bool,
    csv_path: Path | None,
    dry_run: bool,
) -> None:
    log = get_logger("cli.philly_opa")

    if csv_path is None:
        log.info("downloading_opa_csv", force=force_download)
        download_result = download_opa_csv(force=force_download)
        log.info(
            "download_complete",
            path=str(download_result.path),
            bytes=download_result.bytes_written,
            cached=download_result.was_cached,
        )
        csv_path = download_result.path

    if dry_run:
        log.info("dry_run_skipping_db_load", csv_path=str(csv_path))
        return

    session = SessionLocal()
    try:
        loader = load_philly_opa(session, csv_path)
        log.info(
            "starting_load",
            source_id=loader.source_id,
            csv_path=str(csv_path),
            limit=limit,
            batch_size=batch_size,
        )

        run = run_loader(session, loader, batch_size=batch_size, limit=limit)

        log.info(
            "load_complete",
            run_id=str(run.id),
            status=run.status.value,
            rows_seen=run.rows_seen,
            rows_inserted=run.rows_inserted,
            rows_updated=run.rows_updated,
            rows_unchanged=run.rows_unchanged,
            rows_failed=run.rows_failed,
            mapper_seen=loader.stats.seen,
            mapper_mapped=loader.stats.mapped,
            mapper_skipped_no_parcel=loader.stats.skipped_no_parcel,
            mapper_skipped_no_market_value=loader.stats.skipped_no_market_value,
            mapper_skipped_city_owned=loader.stats.skipped_city_owned,
            mapper_failed=loader.stats.failed,
        )
    finally:
        session.close()


@cli.command("download-philly-opa")
@click.option("--force", is_flag=True, help="Redownload even if cached")
def download_philly_opa_cmd(force: bool) -> None:
    log = get_logger("cli.download")
    result = download_opa_csv(force=force)
    log.info(
        "download_result",
        path=str(result.path),
        bytes=result.bytes_written,
        cached=result.was_cached,
    )



@cli.command("download-philly-rtt")
@click.option("--since", default="2021-01-01", help="Earliest display_date to fetch")
@click.option("--force", is_flag=True, help="Redownload even if cached")
def download_philly_rtt_cmd(since: str, force: bool) -> None:
    log = get_logger("cli.download_rtt")
    result = download_rtt_csv(since=since, force=force)
    log.info(
        "rtt_download_result",
        path=str(result.path),
        bytes=result.bytes_written,
        cached=result.was_cached,
    )


@cli.command("load-philly-rtt")
@click.option("--since", default="2021-01-01", help="Earliest display_date to fetch")
@click.option("--limit", type=int, default=None, help="Stop after N source rows")
@click.option("--batch-size", type=int, default=1000, help="Rows per upsert batch")
@click.option("--force-download", is_flag=True, help="Redownload CSV even if cached")
@click.option("--csv-path", type=click.Path(exists=True, path_type=Path), default=None, help="Use a specific CSV file instead of downloading")
@click.option("--dry-run", is_flag=True, help="Skip the database write step")
def load_philly_rtt_cmd(
    since: str,
    limit: int | None,
    batch_size: int,
    force_download: bool,
    csv_path: Path | None,
    dry_run: bool,
) -> None:
    log = get_logger("cli.philly_rtt")

    if csv_path is None:
        log.info("downloading_rtt_csv", since=since, force=force_download)
        download_result = download_rtt_csv(since=since, force=force_download)
        log.info(
            "rtt_download_complete",
            path=str(download_result.path),
            bytes=download_result.bytes_written,
            cached=download_result.was_cached,
        )
        csv_path = download_result.path

    if dry_run:
        log.info("dry_run_skipping_db_load", csv_path=str(csv_path))
        return

    session = SessionLocal()
    try:
        loader = load_philly_rtt(session, csv_path)
        log.info(
            "starting_rtt_load",
            source_id=loader.source_id,
            csv_path=str(csv_path),
            limit=limit,
            batch_size=batch_size,
        )

        run = run_loader(session, loader, batch_size=batch_size, limit=limit)

        log.info(
            "rtt_load_complete",
            run_id=str(run.id),
            status=run.status.value,
            rows_seen=run.rows_seen,
            rows_inserted=run.rows_inserted,
            rows_updated=run.rows_updated,
            rows_unchanged=run.rows_unchanged,
            rows_failed=run.rows_failed,
            mapper_seen=loader.stats.seen,
            mapper_mapped=loader.stats.mapped,
            mapper_skipped_no_parcel=loader.stats.skipped_no_parcel,
            mapper_skipped_no_date=loader.stats.skipped_no_date,
            mapper_skipped_bad_doc_id=loader.stats.skipped_bad_document_id,
            mapper_skipped_no_consideration=loader.stats.skipped_no_consideration,
            mapper_flagged_low=loader.stats.flagged_low_consideration,
            mapper_flagged_overlap=loader.stats.flagged_name_overlap,
            mapper_failed=loader.stats.failed,
            orphans=loader._orphan_count,
                )
    finally:
        session.close()

if __name__ == "__main__":
    cli()