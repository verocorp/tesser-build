from __future__ import annotations

import tesser.testing as ts

import catalog.application.ports.item_repository as item_repository
import catalog.application.service as service
import catalog.client.client as client
import catalog.wiring.wire as wire


@ts.fake
class FakeItemRepository(item_repository.ItemRepository):

    def __init__(self) -> None:
        self.rows: dict[str, item_repository.ItemView] = {}

    def save(self, request: item_repository.SaveItemRequest) -> item_repository.SaveItemResponse:
        self.rows[request.id] = item_repository.ItemView(id=request.id, name=request.name)
        return item_repository.SaveItemResponse()

    def find(
        self, request: item_repository.FindItemRequest
    ) -> item_repository.FoundItem | item_repository.MissingItem:
        row = self.rows.get(request.id)
        if row is None:
            return item_repository.MissingItem()
        return item_repository.FoundItem(item=row)

    def all(self, request: item_repository.ListItemsRequest) -> item_repository.ListItemsResponse:
        return item_repository.ListItemsResponse(items=tuple(self.rows.values()))


def test_add_then_get_returns_the_item() -> None:
    svc = wire.CatalogWiring().client()
    svc.add(client.AddItemRequest(id="a1", name="Anvil"))
    got = svc.get(client.GetItemRequest(id="a1"))
    assert tuple((v.id, v.name) for v in got.items) == (("a1", "Anvil"),)


def test_get_of_an_unknown_item_answers_empty() -> None:
    svc = wire.CatalogWiring().client()
    got = svc.get(client.GetItemRequest(id="nope"))
    assert got.items == ()


def test_the_service_speaks_the_port_not_the_adapter() -> None:
    svc = service.CatalogService(FakeItemRepository())
    svc.add(client.AddItemRequest(id="b2", name="Bellows"))
    got = svc.get(client.GetItemRequest(id="b2"))
    assert tuple(v.name for v in got.items) == ("Bellows",)
