from __future__ import annotations

import tesser.adapters as ts

import catalog.application.ports.item_repository as item_repository


class MemoryItemRepository(ts.Repository):

    def __init__(self) -> None:
        self._rows: dict[str, item_repository.ItemView] = {}

    def save(self, request: item_repository.SaveItemRequest) -> item_repository.SaveItemResponse:
        self._rows[request.id] = item_repository.ItemView(id=request.id, name=request.name)
        return item_repository.SaveItemResponse()

    def find(self, request: item_repository.FindItemRequest) -> item_repository.FindItemResponse:
        row = self._rows.get(request.id)
        if row is None:
            return item_repository.FindItemResponse(found=False, id="", name="")
        return item_repository.FindItemResponse(found=True, id=row.id, name=row.name)

    def all(self, request: item_repository.ListItemsRequest) -> item_repository.ListItemsResponse:
        return item_repository.ListItemsResponse(items=tuple(self._rows.values()))
