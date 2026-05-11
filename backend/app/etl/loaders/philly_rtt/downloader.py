import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import get_settings


logger = logging.getLogger(__name__)

CARTO_BASE_URL = "https://phl.carto.com/api/v2/sql"

RTT_COLUMNS = (
    "document_id",
    "document_type",
    "opa_account_num",
    "display_date",
    "total_consideration",
    "cash_consideration",
    "adjusted_total_consideration",
    "grantors",
    "grantees",
    "street_address",
    "legal_remarks",
    "discrepancy",
)

CACHE_SUBDIR = "philly_rtt"
FILENAME_TEMPLATE = "rtt_deeds_from_{since}_as_of_{date}.csv"


@dataclass(frozen=True, slots=True)
class DownloadResult:
    path: Path
    bytes_written: int
    was_cached: bool
    downloaded_at: datetime


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _build_sql(since: str) -> str:
    cols = ",".join(RTT_COLUMNS)
    return (
        f"SELECT {cols} FROM RTT_SUMMARY "
        f"WHERE document_type='DEED' AND display_date >= '{since}' "
        f"ORDER BY display_date ASC"
    )


def _build_url(since: str) -> str:
    sql = _build_sql(since)
    return f"{CARTO_BASE_URL}?q={quote(sql)}&format=csv"


def _cache_path(cache_dir: Path, since: str, date_str: str) -> Path:
    return cache_dir / CACHE_SUBDIR / FILENAME_TEMPLATE.format(
        since=since.replace("-", ""),
        date=date_str,
    )


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def download_rtt_csv(
    *,
    cache_dir: Path | None = None,
    since: str = "2021-01-01",
    force: bool = False,
    date_str: str | None = None,
    timeout: int | None = None,
) -> DownloadResult:
    settings = get_settings()
    cache_dir = cache_dir or settings.data_cache_dir
    timeout = timeout or settings.http_timeout_seconds
    date_str = date_str or _today_str()

    target = _cache_path(cache_dir, since, date_str)

    if target.exists() and not force:
        stat = target.stat()
        logger.info("Using cached RTT CSV: %s (%d bytes)", target, stat.st_size)
        return DownloadResult(
            path=target,
            bytes_written=stat.st_size,
            was_cached=True,
            downloaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )

    _ensure_dir(target)
    tmp_path = target.with_suffix(target.suffix + ".tmp")

    url = _build_url(since)
    bytes_written = 0
    started = datetime.now(timezone.utc)
    logger.info("Downloading RTT CSV since %s", since)

    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        with tmp_path.open("wb") as f:
            for chunk in response.iter_bytes(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)
                    bytes_written += len(chunk)

    tmp_path.replace(target)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    logger.info("Downloaded %d bytes in %.1fs to %s", bytes_written, elapsed, target)

    return DownloadResult(
        path=target,
        bytes_written=bytes_written,
        was_cached=False,
        downloaded_at=started,
    )