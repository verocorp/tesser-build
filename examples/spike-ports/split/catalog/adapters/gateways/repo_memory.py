from __future__ import annotations

import tesser.adapters as ts

import catalog.application.ports.item_repository as item_repository


class MemoryItemRepository(ts.Repository):

    def __init__(self) -> None:
        self._rows: dict[str, item_repository.ItemView] = {}

    def save(self, request: item_repository.SaveItemRequest) -> item_repository.SaveItemResponse:
        self._rows[request.id] = item_repository.ItemView(id=request.id, name=request.name)
        return item_repository.SaveItemResponse()

    def exists(
        self, request: item_repository.ItemExistsRequest
    ) -> item_repository.ItemExistsResponse:
        return item_repository.ItemExistsResponse(exists=request.id in self._rows)

    def get(self, request: item_repository.GetItemRequest) -> item_repository.GetItemResponse:
        row = self._rows.get(request.id)
        if row is None:
            # Contract violation: get() is only legal once exists() has said
            # True for this id. See the module comment in item_repository.py.
            raise item_repository.ItemNotFoundError(request.id)
        return item_repository.GetItemResponse(id=row.id, name=row.name)

    def all(self, request: item_repository.ListItemsRequest) -> item_repository.ListItemsResponse:
        return item_repository.ListItemsResponse(items=tuple(self._rows.values()))
