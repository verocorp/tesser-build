from __future__ import annotations

import tesser.application as ts

import catalog.application.mapping as mapping
import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.client.client as client
import catalog.domain.item as item


class CatalogService(ts.ApplicationService):

    def __init__(self, items: item_repository.ItemRepository, names: name_policy.NamePolicy) -> None:
        self._items = items
        self._names = names

    def add(self, request: client.AddItemRequest) -> client.AddItemResponse:
        entity = item.Item(item.ItemSpec(id=request.id, name=request.name))
        name_text = entity.name()
        checked = self._names.check(name_policy.CheckNameRequest(name=name_text))
        save_item_request = mapping.save_request(entity)
        self._items.save(save_item_request)
        return mapping.add_response(entity, checked)

    def get(self, request: client.GetItemRequest) -> client.GetItemResponse:
        item_id = item.ItemID(request.id)
        item_id_text = str(item_id)
        found = self._items.find(item_repository.FindItemRequest(id=item_id_text))
        return mapping.get_response(found)

    def list(self, request: client.ListItemsRequest) -> client.ListItemsResponse:
        listed = self._items.all(item_repository.ListItemsRequest())
        return mapping.list_response(listed)
