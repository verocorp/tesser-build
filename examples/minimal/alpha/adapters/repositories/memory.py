from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports as ports


class MemoryWidgetRepository(ts.Repository):

    def __init__(self) -> None:
        self._standing_by_name: dict[str, str] = {}

    def save(self, save_request: ports.SaveRequest) -> ports.SaveResponse:
        self._standing_by_name[save_request.name] = save_request.standing
        return ports.SaveResponse(name=save_request.name)

    def close(self) -> None:
        self._standing_by_name.clear()
