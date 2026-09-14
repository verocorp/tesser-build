from __future__ import annotations

import tesser.adapters as ts

import catalog.application.ports as ports


class MemoryItemRepository(ts.Repository):

    def __init__(self) -> None:
        self._rows: dict[str, ports.Item] = {}

    def save_item(self, save_item_request: ports.SaveItemRequest) -> ports.SaveItemResponse:
        self._rows[save_item_request.id] = ports.Item(
            id=save_item_request.id, name=save_item_request.name
        )
        return ports.SaveItemResponse()

    def find_item(self, find_item_request: ports.FindItemRequest) -> ports.FindItemResponse:
        row = self._rows.get(find_item_request.id)
        if row is None:
            return ports.FindItemResponse(outcome=ports.FindItemOutcome.NOT_FOUND, items=())
        return ports.FindItemResponse(outcome=ports.FindItemOutcome.FOUND, items=(row,))

    def list_items(self, list_items_request: ports.ListItemsRequest) -> ports.ListItemsResponse:
        return ports.ListItemsResponse(items=tuple(self._rows.values()))
