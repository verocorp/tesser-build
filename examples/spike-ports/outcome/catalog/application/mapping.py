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
def get_response(found: item_repository.FindItemResponse) -> client.GetItemResponse:
    if found.outcome == item_repository.MISSING:
        return client.GetItemResponse(items=())
    if found.outcome == item_repository.FOUND:
        return client.GetItemResponse(
            items=tuple(client.ItemView(id=view.id, name=view.name) for view in found.items)
        )
    raise ValueError(f"unrecognized FindItemResponse outcome: {found.outcome!r}")
