from __future__ import annotations

import tesser.testing as ts

import catalog.application as application
import catalog.application.ports as ports
import catalog.client as client
import catalog.component as component


@ts.fake
class FakeItemRepository(ports.ItemRepository):

    def __init__(self, outcome: ports.ItemLookup) -> None:
        self.outcome = outcome
        self.rows: dict[str, ports.ItemView] = {}

    def save(self, save_item_request: ports.SaveItemRequest) -> ports.SaveItemResponse:
        self.rows[save_item_request.id] = ports.ItemView(
            id=save_item_request.id, name=save_item_request.name
        )
        return ports.SaveItemResponse()

    def find(self, find_item_request: ports.FindItemRequest) -> ports.FindItemResponse:
        row = self.rows.get(find_item_request.id)
        if row is None:
            return ports.FindItemResponse(outcome=ports.ItemLookup.MISSING, items=())
        return ports.FindItemResponse(outcome=self.outcome, items=(row,))

    def all(self, list_items_request: ports.ListItemsRequest) -> ports.ListItemsResponse:
        return ports.ListItemsResponse(items=tuple(self.rows.values()))


@ts.fake
class FakeNamePolicy(ports.NamePolicy):

    def __init__(self, verdict: ports.NameVerdict) -> None:
        self.verdict = verdict

    def check(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        return ports.CheckNameResponse(verdict=self.verdict, reason="fixed")


def test_add_then_get_returns_the_item() -> None:
    catalog_client = component.Catalog().client
    catalog_client.add(client.AddItemRequest(id="a1", name="Anvil"))
    get_item_response = catalog_client.get(client.GetItemRequest(id="a1"))
    assert tuple((v.id, v.name) for v in get_item_response.items) == (("a1", "Anvil"),)


def test_get_of_an_unknown_item_answers_empty() -> None:
    catalog_client = component.Catalog().client
    get_item_response = catalog_client.get(client.GetItemRequest(id="nope"))
    assert get_item_response.items == ()


def test_an_archived_item_is_not_served_as_live() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.ARCHIVED),
        FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED),
    )
    catalog_service.add(client.AddItemRequest(id="b2", name="Bellows"))
    get_item_response = catalog_service.get(client.GetItemRequest(id="b2"))
    assert get_item_response.items == ()


def test_a_reserved_name_is_refused_with_a_reason() -> None:
    catalog_client = component.Catalog().client
    add_item_response = catalog_client.add(client.AddItemRequest(id="c3", name="admin"))
    assert add_item_response.items == ()
    assert add_item_response.reason == "name is reserved"


def test_list_returns_every_stored_item() -> None:
    catalog_client = component.Catalog().client
    catalog_client.add(client.AddItemRequest(id="d4", name="Drill"))
    list_items_response = catalog_client.list(client.ListItemsRequest())
    assert tuple(v.name for v in list_items_response.items) == ("Drill",)
