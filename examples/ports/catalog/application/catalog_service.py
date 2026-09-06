from __future__ import annotations

import typing

import tesser.application as ts

import catalog.application.ports as ports
import catalog.client as client
import catalog.domain as domain


class MapToItemView(ts.Mapper, client.ItemView):

    def __init__(self, item_view: ports.ItemView) -> None:
        super().__init__(id=item_view.id, name=item_view.name)


class MapToAddedItemView(ts.Mapper, client.ItemView):

    def __init__(self, item: domain.Item) -> None:
        super().__init__(id=item.id(), name=item.name())


class MapToGetItemResponse(ts.Mapper, client.GetItemResponse):

    def __init__(self, find_item_response: ports.FindItemResponse) -> None:
        items: tuple[client.ItemView, ...]
        match find_item_response.outcome:
            case ports.ItemLookup.FOUND:
                items = tuple(
                    MapToItemView(item_view=item_view) for item_view in find_item_response.items
                )
            case ports.ItemLookup.ARCHIVED:
                items = ()
            case ports.ItemLookup.MISSING:
                items = ()
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(items=items)


class MapToAddItemResponse(ts.Mapper, client.AddItemResponse):

    def __init__(self, item: domain.Item, check_name_response: ports.CheckNameResponse) -> None:
        items: tuple[client.ItemView, ...]
        match check_name_response.verdict:
            case ports.NameVerdict.ALLOWED:
                items = (MapToAddedItemView(item=item),)
            case ports.NameVerdict.RESERVED:
                items = ()
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(items=items, reason=check_name_response.reason)


class CatalogService(ts.ApplicationService):

    def __init__(
        self, item_repository: ports.ItemRepository, name_policy: ports.NamePolicy
    ) -> None:
        self._item_repository = item_repository
        self._name_policy = name_policy

    def add(self, add_item_request: client.AddItemRequest) -> client.AddItemResponse:
        item = domain.Item(domain.ItemSpec(id=add_item_request.id, name=add_item_request.name))
        name_text = item.name()
        check_name_response = self._name_policy.check(ports.CheckNameRequest(name=name_text))
        item_id_text = item.id()
        item_name_text = item.name()
        save_item_request = ports.SaveItemRequest(id=item_id_text, name=item_name_text)
        self._item_repository.save(save_item_request)
        return MapToAddItemResponse(item=item, check_name_response=check_name_response)

    def get(self, get_item_request: client.GetItemRequest) -> client.GetItemResponse:
        item_id = domain.ItemID(get_item_request.id)
        item_id_text = str(item_id)
        find_item_response = self._item_repository.find(ports.FindItemRequest(id=item_id_text))
        return MapToGetItemResponse(find_item_response=find_item_response)

    def list(self, list_items_request: client.ListItemsRequest) -> client.ListItemsResponse:
        list_items_response = self._item_repository.all(ports.ListItemsRequest())
        item_views = tuple(
            client.ItemView(id=item_view.id, name=item_view.name)
            for item_view in list_items_response.items
        )
        return client.ListItemsResponse(items=item_views)
