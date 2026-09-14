from __future__ import annotations

import tesser.testing as ts

import catalog.application as application
import catalog.application.ports as ports
import catalog.client as client
import catalog.component as component


@ts.fake
class FakeItemRepository(ports.ItemRepository):

    def __init__(self, outcome: ports.FindItemOutcome) -> None:
        self.outcome = outcome
        self.rows: dict[str, ports.Item] = {}

    def save_item(self, save_item_request: ports.SaveItemRequest) -> ports.SaveItemResponse:
        self.rows[save_item_request.id] = ports.Item(
            id=save_item_request.id, name=save_item_request.name
        )
        return ports.SaveItemResponse()

    def find_item(self, find_item_request: ports.FindItemRequest) -> ports.FindItemResponse:
        row = self.rows.get(find_item_request.id)
        if row is None:
            return ports.FindItemResponse(outcome=ports.FindItemOutcome.NOT_FOUND, items=())
        return ports.FindItemResponse(outcome=self.outcome, items=(row,))

    def list_items(self, list_items_request: ports.ListItemsRequest) -> ports.ListItemsResponse:
        return ports.ListItemsResponse(items=tuple(self.rows.values()))


@ts.fake
class FakeNamePolicy(ports.NamePolicy):

    def __init__(self, outcome: ports.CheckNameOutcome) -> None:
        self.outcome = outcome

    def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        return ports.CheckNameResponse(outcome=self.outcome, reason="fixed")


def test_add_then_get_returns_the_item() -> None:
    catalog_client = component.Catalog().client
    catalog_client.add_item(client.AddItemRequest(id="a1", name="Anvil"))
    get_item_response = catalog_client.get_item(client.GetItemRequest(id="a1"))
    assert tuple((v.id, v.name) for v in get_item_response.items) == (("a1", "Anvil"),)


def test_get_of_an_unknown_item_answers_empty() -> None:
    catalog_client = component.Catalog().client
    get_item_response = catalog_client.get_item(client.GetItemRequest(id="nope"))
    assert get_item_response.items == ()


def test_an_archived_item_is_not_served_as_live() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.FindItemOutcome.ARCHIVED),
        FakeNamePolicy(outcome=ports.CheckNameOutcome.ALLOWED),
    )
    catalog_service.add_item(client.AddItemRequest(id="b2", name="Bellows"))
    get_item_response = catalog_service.get_item(client.GetItemRequest(id="b2"))
    assert get_item_response.items == ()


def test_a_reserved_name_is_refused_with_a_reason() -> None:
    catalog_client = component.Catalog().client
    add_item_response = catalog_client.add_item(client.AddItemRequest(id="c3", name="admin"))
    assert add_item_response.items == ()
    assert add_item_response.reason == "name is reserved"


def test_list_returns_every_stored_item() -> None:
    catalog_client = component.Catalog().client
    catalog_client.add_item(client.AddItemRequest(id="d4", name="Drill"))
    list_items_response = catalog_client.list_items(client.ListItemsRequest())
    assert tuple(v.name for v in list_items_response.items) == ("Drill",)
