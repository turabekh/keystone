from app.etl.hashing import compute_payload_hash


def test_hash_is_deterministic():
    payload = {"a": 1, "b": "two", "c": [1, 2, 3]}
    assert compute_payload_hash(payload) == compute_payload_hash(payload)


def test_hash_is_order_independent():
    p1 = {"a": 1, "b": 2, "c": 3}
    p2 = {"c": 3, "b": 2, "a": 1}
    assert compute_payload_hash(p1) == compute_payload_hash(p2)


def test_hash_changes_on_value_change():
    p1 = {"a": 1, "b": 2}
    p2 = {"a": 1, "b": 3}
    assert compute_payload_hash(p1) != compute_payload_hash(p2)


def test_hash_handles_none():
    p1 = {"a": 1, "b": None}
    p2 = {"a": 1, "b": None}
    assert compute_payload_hash(p1) == compute_payload_hash(p2)


def test_hash_handles_nested():
    p1 = {"a": {"x": 1, "y": 2}}
    p2 = {"a": {"y": 2, "x": 1}}
    assert compute_payload_hash(p1) == compute_payload_hash(p2)


def test_hash_handles_dates():
    from datetime import date

    payload = {"sale_date": date(2024, 1, 15)}
    h1 = compute_payload_hash(payload)
    h2 = compute_payload_hash({"sale_date": "2024-01-15"})
    assert h1 == h2