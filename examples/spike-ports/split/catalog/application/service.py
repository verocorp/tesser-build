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
        # The split port makes the two-step shape explicit at the call site:
        # ask exists() first, and only call get() once exists() has said
        # True for this same id. Skipping straight to get() on an id that
        # may not exist would violate the port's precondition (see the
        # module comment in item_repository.py).
        answer = self._items.exists(item_repository.ItemExistsRequest(id=request.id))
        if not answer.exists:
            return mapping.missing_response()
        got = self._items.get(item_repository.GetItemRequest(id=request.id))
        return mapping.found_response(got)
