from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.etl.loaders.philly_opa.downloader import (
    DownloadResult,
    _cache_path,
    _today_str,
    download_opa_csv,
)


@pytest.fixture
def tmp_cache(tmp_path):
    return tmp_path / "cache"


def _mock_stream_response(body: bytes, status_code: int = 200):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "boom",
            request=MagicMock(),
            response=MagicMock(status_code=status_code),
        )
    response.iter_bytes = MagicMock(return_value=iter([body]))
    context = MagicMock()
    context.__enter__ = MagicMock(return_value=response)
    context.__exit__ = MagicMock(return_value=False)
    return context


def test_cache_path_format():
    p = _cache_path(Path("/tmp/cache"), "20260511")
    assert p == Path("/tmp/cache/philly_opa/opa_properties_20260511.csv")


def test_today_str_is_eight_digits():
    s = _today_str()
    assert len(s) == 8
    assert s.isdigit()


@patch("app.etl.loaders.philly_opa.downloader.httpx.stream")
def test_download_writes_file(mock_stream, tmp_cache):
    mock_stream.return_value = _mock_stream_response(b"col1,col2\n1,2\n")

    result = download_opa_csv(cache_dir=tmp_cache, date_str="20260511")

    assert result.was_cached is False
    assert result.path.exists()
    assert result.path.read_bytes() == b"col1,col2\n1,2\n"
    assert result.bytes_written == 14


@patch("app.etl.loaders.philly_opa.downloader.httpx.stream")
def test_download_uses_cache_on_second_call(mock_stream, tmp_cache):
    mock_stream.return_value = _mock_stream_response(b"data")

    r1 = download_opa_csv(cache_dir=tmp_cache, date_str="20260511")
    assert r1.was_cached is False
    assert mock_stream.call_count == 1

    r2 = download_opa_csv(cache_dir=tmp_cache, date_str="20260511")
    assert r2.was_cached is True
    assert mock_stream.call_count == 1


@patch("app.etl.loaders.philly_opa.downloader.httpx.stream")
def test_force_bypasses_cache(mock_stream, tmp_cache):
    mock_stream.return_value = _mock_stream_response(b"v1")

    download_opa_csv(cache_dir=tmp_cache, date_str="20260511")
    mock_stream.return_value = _mock_stream_response(b"v2")

    r2 = download_opa_csv(cache_dir=tmp_cache, date_str="20260511", force=True)
    assert r2.was_cached is False
    assert r2.path.read_bytes() == b"v2"


@patch("app.etl.loaders.philly_opa.downloader.httpx.stream")
def test_partial_download_does_not_overwrite_cache(mock_stream, tmp_cache):
    mock_stream.return_value = _mock_stream_response(b"good")
    download_opa_csv(cache_dir=tmp_cache, date_str="20260511")

    cached_path = tmp_cache / "philly_opa" / "opa_properties_20260511.csv"
    assert cached_path.read_bytes() == b"good"

    failing_response = MagicMock()
    failing_response.raise_for_status = MagicMock()
    failing_response.iter_bytes = MagicMock(side_effect=RuntimeError("network died"))
    failing_context = MagicMock()
    failing_context.__enter__ = MagicMock(return_value=failing_response)
    failing_context.__exit__ = MagicMock(return_value=False)
    mock_stream.return_value = failing_context

    with pytest.raises(RuntimeError):
        download_opa_csv(cache_dir=tmp_cache, date_str="20260511", force=True)

    assert cached_path.read_bytes() == b"good"


@patch("app.etl.loaders.philly_opa.downloader.httpx.stream")
def test_http_error_raises(mock_stream, tmp_cache):
    mock_stream.return_value = _mock_stream_response(b"", status_code=500)

    with pytest.raises(httpx.HTTPStatusError):
        download_opa_csv(cache_dir=tmp_cache, date_str="20260511")


@patch("app.etl.loaders.philly_opa.downloader.httpx.stream")
def test_creates_nested_cache_directory(mock_stream, tmp_cache):
    mock_stream.return_value = _mock_stream_response(b"data")

    result = download_opa_csv(cache_dir=tmp_cache, date_str="20260511")

    assert result.path.parent.exists()
    assert result.path.parent.name == "philly_opa"


@patch("app.etl.loaders.philly_opa.downloader.httpx.stream")
def test_download_streams_multiple_chunks(mock_stream, tmp_cache):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.iter_bytes = MagicMock(return_value=iter([b"chunk1", b"chunk2", b"chunk3"]))
    context = MagicMock()
    context.__enter__ = MagicMock(return_value=response)
    context.__exit__ = MagicMock(return_value=False)
    mock_stream.return_value = context

    result = download_opa_csv(cache_dir=tmp_cache, date_str="20260511")

    assert result.path.read_bytes() == b"chunk1chunk2chunk3"
    assert result.bytes_written == 18


def test_download_result_is_immutable():
    from datetime import datetime, timezone
    r = DownloadResult(
        path=Path("/tmp/x"),
        bytes_written=100,
        was_cached=False,
        downloaded_at=datetime.now(timezone.utc),
    )
    with pytest.raises(Exception):
        r.bytes_written = 200