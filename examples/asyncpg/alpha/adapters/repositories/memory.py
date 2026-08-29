from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.widget_repository as widget_repository


class MemoryWidgetRepository(ts.Repository):

    def __init__(self) -> None:
        self._names: set[str] = set()

    async def save(self, request: widget_repository.SaveRequest) -> widget_repository.SaveResponse:
        self._names.add(request.name)
        return widget_repository.SaveResponse(name=request.name)

    async def find(self, request: widget_repository.FindRequest) -> widget_repository.FindResponse:
        found = widget_repository.Found.YES if request.name in self._names else widget_repository.Found.NO
        return widget_repository.FindResponse(found=found)

    async def close(self) -> None:
        self._names.clear()
