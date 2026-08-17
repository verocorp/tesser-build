from __future__ import annotations

import typing

import tesser.application as ts

import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.client.client as client
import catalog.domain.item as item


@ts.do_not_use_function
def save_request(entity: item.Item) -> item_repository.SaveItemRequest:
    return item_repository.SaveItemRequest(id=entity.id(), name=entity.name())


@ts.do_not_use_function
def item_spec(view: item_repository.ItemView) -> item.ItemSpec:
    return item.ItemSpec(id=view.id, name=view.name)


@ts.do_not_use_function
def rebuilt(view: item_repository.ItemView) -> item.Item:
    return item.Item(item_spec(view))


@ts.do_not_use_function
def get_response(found: item_repository.FindItemResponse) -> client.GetItemResponse:
    match found.outcome:
        case item_repository.ItemLookup.FOUND:
            return client.GetItemResponse(items=_views(found.items))
        case item_repository.ItemLookup.ARCHIVED:
            return client.GetItemResponse(items=())
        case item_repository.ItemLookup.MISSING:
            return client.GetItemResponse(items=())
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def list_response(listed: item_repository.ListItemsResponse) -> client.ListItemsResponse:
    return client.ListItemsResponse(items=_views(listed.items))


@ts.do_not_use_function
def add_response(entity: item.Item, checked: name_policy.CheckNameResponse) -> client.AddItemResponse:
    match checked.verdict:
        case name_policy.NameVerdict.ALLOWED:
            return client.AddItemResponse(id=entity.id(), name=entity.name(), reason="")
        case name_policy.NameVerdict.RESERVED:
            return client.AddItemResponse(id="", name="", reason=checked.reason)
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def _views(views: tuple[item_repository.ItemView, ...]) -> tuple[client.ItemView, ...]:
    return tuple(client.ItemView(id=view.id, name=view.name) for view in views)
