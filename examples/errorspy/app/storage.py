"""A fake vendor storage layer — the "outside" the adapter translates from.

Its errors are vendor-shaped (StorageMiss, StorageUnavailable) and its records
are raw primitive dicts. Nothing here knows about the domain. The repository
adapter (repository.py) is the ONLY thing that touches these types; it turns a
miss into a domain not_found, an outage into an InfraError, and a record that
fails reconstruction into a corrupted-record InfraError. Nothing vendor-shaped
crosses inward.
"""

from __future__ import annotations

from typing import Any


class StorageError(Exception):
    """Base for vendor-shaped failures. Must never cross into the domain."""


class StorageMiss(StorageError):
    """No row for the key. The adapter maps this to a domain not_found."""


class StorageUnavailable(StorageError):
    """Driver/connection failure. The adapter maps this to an InfraError (503)."""


Record = dict[str, Any]


class FakeStorage:
    """An in-memory stand-in for a real datastore. ``down`` forces the outage
    path; records are raw dicts that may be deliberately corrupt (see B7)."""

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
