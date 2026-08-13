from __future__ import annotations

import tesser.application as ts

import catalog.application.ports.item_repository as item_repository
import catalog.client.client as client
import catalog.domain.item as item


@ts.function
def save_request(entity: item.Item) -> item_repository.SaveItemRequest:
    return item_repository.SaveItemRequest(id=entity.id(), name=entity.name())


@ts.function
def rebuilt(view: item_repository.ItemView) -> item.Item:
    return item.Item(item_spec(view))


@ts.function
def item_spec(view: item_repository.ItemView) -> item.ItemSpec:
    return item.ItemSpec(id=view.id, name=view.name)


@ts.function
def found_response(got: item_repository.GetItemResponse) -> client.GetItemResponse:
    return client.GetItemResponse(items=(client.ItemView(id=got.id, name=got.name),))


@ts.function
def missing_response() -> client.GetItemResponse:
    return client.GetItemResponse(items=())
