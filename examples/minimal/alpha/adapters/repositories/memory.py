from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.whole_repository as whole_repository
import tesser.errors as errors


class MemoryWholeRepository(ts.Repository):

    def __init__(self) -> None:
        self._rows: dict[str, whole_repository.WholeRecord] = {}
        self._open = True

    def save(self, request: whole_repository.SaveWholeRequest) -> whole_repository.SaveWholeResponse:
        if not self._open:
            raise errors.InfraError("repository is closed")
        self._rows[request.id] = whole_repository.WholeRecord(request.id, request.name, request.count)
        return whole_repository.SaveWholeResponse()

    def find(self, request: whole_repository.FindWholeRequest) -> whole_repository.FindWholeResponse:
        row = self._rows.get(request.id)
        if row is None:
            return whole_repository.FindWholeResponse(whole_repository.Lookup.ABSENT, ())
        return whole_repository.FindWholeResponse(whole_repository.Lookup.PRESENT, (row,))

    def close(self) -> None:
        self._open = False
