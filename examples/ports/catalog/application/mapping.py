from __future__ import annotations

import typing

import tesser.application as ts

import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.client.client as client
import catalog.domain.item as item


@ts.do_not_use_function
def get_response(found: item_repository.FindItemResponse) -> client.GetItemResponse:  # tesser:debt TB051
    match found.outcome:
        case item_repository.ItemLookup.FOUND:
            views = tuple(client.ItemView(id=view.id, name=view.name) for view in found.items)
            return client.GetItemResponse(items=views)
        case item_repository.ItemLookup.ARCHIVED:
            return client.GetItemResponse(items=())
        case item_repository.ItemLookup.MISSING:
            return client.GetItemResponse(items=())
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def add_response(entity: item.Item, checked: name_policy.CheckNameResponse) -> client.AddItemResponse:  # tesser:debt TB051
    match checked.verdict:
        case name_policy.NameVerdict.ALLOWED:
            return client.AddItemResponse(id=entity.id(), name=entity.name(), reason="")
        case name_policy.NameVerdict.RESERVED:
            return client.AddItemResponse(id="", name="", reason=checked.reason)
        case _ as unreachable:
            typing.assert_never(unreachable)
