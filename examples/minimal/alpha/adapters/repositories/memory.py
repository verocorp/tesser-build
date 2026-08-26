from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.thing_repository as thing_repository
import tesser.errors as errors


class MemoryThingRepository(ts.Repository):

    def __init__(self) -> None:
        self._names: set[str] = set()
        self._open = True

    def save(self, request: thing_repository.SaveRequest) -> thing_repository.SaveResponse:
        if not self._open:
            raise errors.InfraError("repository is closed")
        self._names.add(request.name)
        return thing_repository.SaveResponse()

    def close(self) -> None:
        self._open = False
