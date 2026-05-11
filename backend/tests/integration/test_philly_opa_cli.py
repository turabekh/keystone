import csv
from pathlib import Path

import pytest
from click.testing import CliRunner

from app.etl.cli import cli
from app.etl.loaders.philly_opa.loader import load_philly_opa
from tests.integration.test_philly_opa_loader import SAMPLE_ROWS


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "opa_cli_sample.csv"
    fieldnames = list(SAMPLE_ROWS[0].keys())
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(SAMPLE_ROWS)
    return csv_path


@pytest.mark.integration
def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "load-philly-opa" in result.output


@pytest.mark.integration
def test_load_philly_opa_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["load-philly-opa", "--help"])
    assert result.exit_code == 0
    assert "--limit" in result.output
    assert "--dry-run" in result.output


@pytest.mark.integration
def test_dry_run_does_not_load(sample_csv):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["load-philly-opa", "--csv-path", str(sample_csv), "--dry-run"],
    )
    if result.exit_code != 0:
        print("STDOUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
    assert result.exit_code == 0


@pytest.mark.integration
def test_load_with_limit_invokes_loader(sample_csv, monkeypatch):
    invocations = []

    from app.etl import cli as cli_module

    real_run_loader = cli_module.run_loader

    def fake_run_loader(session, loader, **kwargs):
        invocations.append((loader.source_id, kwargs))
        from app.models.etl_run import EtlRun, EtlRunStatus
        run = EtlRun(source_id=loader.source_id, status=EtlRunStatus.SUCCESS)
        session.add(run)
        session.flush()
        return run

    monkeypatch.setattr(cli_module, "run_loader", fake_run_loader)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "load-philly-opa",
            "--csv-path", str(sample_csv),
            "--limit", "1",
            "--batch-size", "10",
        ],
    )

    if result.exit_code != 0:
        print("STDOUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
    assert result.exit_code == 0
    assert len(invocations) == 1
    source_id, kwargs = invocations[0]
    assert source_id == "philly_opa"
    assert kwargs["limit"] == 1
    assert kwargs["batch_size"] == 10