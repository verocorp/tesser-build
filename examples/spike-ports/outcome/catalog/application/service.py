from __future__ import annotations

import tesser.application as ts

import catalog.application.mapping as mapping
import catalog.application.ports.item_repository as item_repository
import catalog.client.client as client
import catalog.domain.item as item


class CatalogService(ts.ApplicationService):

    def __init__(self, items: item_repository.ItemRepository) -> None:
        self._items = items

    def add(self, request: client.AddItemRequest) -> client.AddItemResponse:
        entity = item.Item(item.ItemSpec(id=request.id, name=request.name))
        self._items.save(mapping.save_request(entity))
        return client.AddItemResponse(id=entity.id(), name=entity.name())

    def get(self, request: client.GetItemRequest) -> client.GetItemResponse:
        found = self._items.find(item_repository.FindItemRequest(id=request.id))
        return mapping.get_response(found)
