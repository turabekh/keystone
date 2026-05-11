from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class SourceRow:
    natural_key: str
    payload: dict[str, Any]


class Loader(Protocol):
    source_id: str

    def fetch(self) -> Iterator[SourceRow]:
        ...

    def upsert_batch(self, session: Any, rows: list[SourceRow]) -> "UpsertResult":
        ...


@dataclass(slots=True)
class UpsertResult:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0

    def __iadd__(self, other: "UpsertResult") -> "UpsertResult":
        self.inserted += other.inserted
        self.updated += other.updated
        self.unchanged += other.unchanged
        self.failed += other.failed
        return self