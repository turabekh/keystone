from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from validation import ExpectedCase, load_validation_set, run_case


VALIDATION_FIXTURE = (
    Path(__file__).resolve().parent.parent.parent
    / "validation"
    / "fixtures"
    / "v1_validation_set.yaml"
)


def _load_cases() -> list[ExpectedCase]:
    return load_validation_set(VALIDATION_FIXTURE)


def _case_id(case: ExpectedCase) -> str:
    return case.test_id


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.integration
@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_validation_case(case: ExpectedCase, client: TestClient) -> None:
    outcome = run_case(client, case)
    
    if not outcome.passed:
        failure_summary = "\n".join(f"  - {f}" for f in outcome.failures)
        notes_section = (
            f"\n\nCase notes:\n{case.notes.rstrip()}"
            if case.notes.strip() else ""
        )
        pytest.fail(
            f"Validation case {case.test_id!r} failed for "
            f"{case.address_query!r}:\n{failure_summary}{notes_section}"
        )