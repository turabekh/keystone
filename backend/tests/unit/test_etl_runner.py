from app.etl.runner import batched
from app.etl.types import SourceRow, UpsertResult

def test_split_into_safe_batches_passes_through_small():
    from app.etl.loaders.philly_opa.loader import _split_into_safe_batches
    rows = [SourceRow(natural_key=str(i), payload={"n": i}) for i in range(100)]
    batches = list(_split_into_safe_batches(rows))
    assert len(batches) == 1
    assert len(batches[0]) == 100


def test_split_into_safe_batches_splits_large():
    from app.etl.loaders.philly_opa.loader import SAFE_BATCH_LIMIT, _split_into_safe_batches
    n = SAFE_BATCH_LIMIT * 2 + 50
    rows = [SourceRow(natural_key=str(i), payload={"n": i}) for i in range(n)]
    batches = list(_split_into_safe_batches(rows))
    assert len(batches) == 3
    assert sum(len(b) for b in batches) == n
    assert all(len(b) <= SAFE_BATCH_LIMIT for b in batches)


def test_deduplicate_by_natural_key():
    from app.etl.loaders.philly_opa.loader import _deduplicate_by_natural_key
    rows = [
        SourceRow(natural_key="a", payload={"v": 1}),
        SourceRow(natural_key="b", payload={"v": 2}),
        SourceRow(natural_key="a", payload={"v": 3}),
        SourceRow(natural_key="c", payload={"v": 4}),
    ]
    result = _deduplicate_by_natural_key(rows)
    assert [r.natural_key for r in result] == ["a", "b", "c"]
    assert result[0].payload == {"v": 1}


def test_safe_batch_limit_under_postgres_limit():
    from app.etl.loaders.philly_opa.loader import (
        PARAMS_PER_PROPERTY_ROW,
        POSTGRES_PARAM_LIMIT,
        SAFE_BATCH_LIMIT,
    )
    assert SAFE_BATCH_LIMIT * PARAMS_PER_PROPERTY_ROW < POSTGRES_PARAM_LIMIT
    
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