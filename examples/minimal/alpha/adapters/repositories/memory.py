from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.widget_repository as widget_repository


class MemoryWidgetRepository(ts.Repository):

    def __init__(self) -> None:
        self._standing_by_name: dict[str, str] = {}

    def save(self, request: widget_repository.SaveRequest) -> widget_repository.SaveResponse:
        self._standing_by_name[request.name] = request.standing
        return widget_repository.SaveResponse(name=request.name)

    def close(self) -> None:
        self._standing_by_name.clear()
