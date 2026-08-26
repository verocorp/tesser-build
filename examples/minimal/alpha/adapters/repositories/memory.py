from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.thing_repository as thing_repository


class MemoryThingRepository(ts.Repository):

    def __init__(self) -> None:
        self._names: set[str] = set()

    def save(self, request: thing_repository.SaveRequest) -> thing_repository.SaveResponse:
        self._names.add(request.name)
        return thing_repository.SaveResponse()

    def close(self) -> None:
        self._names.clear()
