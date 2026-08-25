from __future__ import annotations

import typing

import tesser.application as ts

import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.client.client as client
import catalog.domain.item as item


class MapToItemView(ts.Mapper, client.ItemView):

    def __init__(self, view: item_repository.ItemView) -> None:
        super().__init__(id=view.id, name=view.name)


class MapToAddedItemView(ts.Mapper, client.ItemView):

    def __init__(self, entity: item.Item) -> None:
        super().__init__(id=entity.id(), name=entity.name())


class MapToGetItemResponse(ts.Mapper, client.GetItemResponse):

    def __init__(self, found: item_repository.FindItemResponse) -> None:
        items: tuple[client.ItemView, ...]
        match found.outcome:
            case item_repository.ItemLookup.FOUND:
                items = tuple(MapToItemView(view=view) for view in found.items)
            case item_repository.ItemLookup.ARCHIVED:
                items = ()
            case item_repository.ItemLookup.MISSING:
                items = ()
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(items=items)


class MapToAddItemResponse(ts.Mapper, client.AddItemResponse):

    def __init__(self, entity: item.Item, checked: name_policy.CheckNameResponse) -> None:
        items: tuple[client.ItemView, ...]
        match checked.verdict:
            case name_policy.NameVerdict.ALLOWED:
                items = (MapToAddedItemView(entity=entity),)
            case name_policy.NameVerdict.RESERVED:
                items = ()
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(items=items, reason=checked.reason)
