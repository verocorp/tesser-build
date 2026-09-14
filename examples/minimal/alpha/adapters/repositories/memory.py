from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports as ports


class MemoryWidgetRepository(ts.Repository):

    def __init__(self) -> None:
        self._standing_by_name: dict[str, str] = {}

    def save_widget(self, save_widget_request: ports.SaveWidgetRequest) -> ports.SaveWidgetResponse:
        self._standing_by_name[save_widget_request.name] = save_widget_request.standing
        return ports.SaveWidgetResponse(name=save_widget_request.name)

    def close(self) -> None:
        self._standing_by_name.clear()
