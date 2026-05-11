from app.etl.runner import batched
from app.etl.types import SourceRow, UpsertResult


def test_batched_yields_correct_size():
    rows = [SourceRow(natural_key=str(i), payload={"n": i}) for i in range(25)]
    batches = list(batched(iter(rows), size=10))
    assert len(batches) == 3
    assert len(batches[0]) == 10
    assert len(batches[1]) == 10
    assert len(batches[2]) == 5


def test_batched_empty_input():
    batches = list(batched(iter([]), size=10))
    assert batches == []


def test_batched_single_batch():
    rows = [SourceRow(natural_key=str(i), payload={}) for i in range(5)]
    batches = list(batched(iter(rows), size=10))
    assert len(batches) == 1
    assert len(batches[0]) == 5


def test_upsert_result_addition():
    a = UpsertResult(inserted=2, updated=3, unchanged=5, failed=0)
    b = UpsertResult(inserted=1, updated=1, unchanged=2, failed=1)
    a += b
    assert a.inserted == 3
    assert a.updated == 4
    assert a.unchanged == 7
    assert a.failed == 1