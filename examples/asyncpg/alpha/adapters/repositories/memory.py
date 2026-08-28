from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.widget_repository as widget_repository


class MemoryWidgetRepository(ts.Repository):

    def __init__(self) -> None:
        self._names: set[str] = set()

    async def save(self, request: widget_repository.SaveRequest) -> widget_repository.SaveResponse:
        self._names.add(request.name)
        return widget_repository.SaveResponse(name=request.name)

    async def close(self) -> None:
        self._names.clear()
