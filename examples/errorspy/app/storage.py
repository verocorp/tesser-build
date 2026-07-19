from __future__ import annotations

from typing import Any


class StorageError(Exception):
    pass


class StorageMiss(StorageError):
    pass


class StorageUnavailable(StorageError):
    pass


Record = dict[str, Any]


class FakeStorage:

    def __init__(self, *, down: bool = False) -> None:
        self._rows: dict[str, Record] = {}
        self.down = down

    def put(self, key: str, record: Record) -> None:
        self._rows[key] = record

    def load(self, key: str) -> Record:
        if self.down:
            raise StorageUnavailable(f"storage is unavailable (loading {key!r})")
        try:
            return self._rows[key]
        except KeyError as e:
            raise StorageMiss(f"no row for {key!r}") from e
