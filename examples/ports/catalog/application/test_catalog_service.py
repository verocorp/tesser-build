from __future__ import annotations

import pytest
import tesser.testing as ts

import catalog.application as application
import catalog.application.ports as ports
import catalog.client as client
import catalog.domain as domain


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

    def __init__(self, verdict: ports.NameVerdict, reason: str) -> None:
        self.verdict = verdict
        self.reason = reason
        self.asked: list[str] = []

    def check(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        self.asked.append(check_name_request.name)
        return ports.CheckNameResponse(verdict=self.verdict, reason=self.reason)


def test_adding_an_item_answers_with_what_was_stored() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.FOUND),
        FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED, reason=""),
    )
    add_item_response = catalog_service.add(client.AddItemRequest(id="a1", name="Anvil"))
    assert tuple((v.id, v.name) for v in add_item_response.items) == (("a1", "Anvil"),)
    assert add_item_response.reason == ""


def test_adding_an_item_asks_the_policy_about_the_requested_name() -> None:
    fake_name_policy = FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED, reason="")
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.FOUND), fake_name_policy
    )
    catalog_service.add(client.AddItemRequest(id="a1", name="Anvil"))
    assert fake_name_policy.asked == ["Anvil"]


def test_a_refused_name_answers_blank_with_the_reason_the_policy_gave() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.FOUND),
        FakeNamePolicy(verdict=ports.NameVerdict.RESERVED, reason="name is reserved"),
    )
    add_item_response = catalog_service.add(client.AddItemRequest(id="c3", name="admin"))
    assert add_item_response.items == ()
    assert add_item_response.reason == "name is reserved"


def test_an_item_with_no_name_is_refused_before_any_port_is_touched() -> None:
    fake_item_repository = FakeItemRepository(outcome=ports.ItemLookup.FOUND)
    fake_name_policy = FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED, reason="")
    catalog_service = application.CatalogService(fake_item_repository, fake_name_policy)
    with pytest.raises(ValueError, match="name must be non-empty"):
        catalog_service.add(client.AddItemRequest(id="a1", name=""))
    assert fake_item_repository.rows == {}
    assert fake_name_policy.asked == []


def test_getting_an_added_item_answers_it() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.FOUND),
        FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED, reason=""),
    )
    catalog_service.add(client.AddItemRequest(id="a1", name="Anvil"))
    get_item_response = catalog_service.get(client.GetItemRequest(id="a1"))
    assert tuple((view.id, view.name) for view in get_item_response.items) == (("a1", "Anvil"),)


def test_getting_an_id_that_was_never_added_answers_nothing() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.FOUND),
        FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED, reason=""),
    )
    get_item_response = catalog_service.get(client.GetItemRequest(id="ghost"))
    assert get_item_response.items == ()


def test_an_archived_item_is_not_served_as_live() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.ARCHIVED),
        FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED, reason=""),
    )
    catalog_service.add(client.AddItemRequest(id="b2", name="Bellows"))
    get_item_response = catalog_service.get(client.GetItemRequest(id="b2"))
    assert get_item_response.items == ()


def test_listing_answers_every_added_item() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.FOUND),
        FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED, reason=""),
    )
    catalog_service.add(client.AddItemRequest(id="a1", name="Anvil"))
    catalog_service.add(client.AddItemRequest(id="b2", name="Bellows"))
    list_items_response = catalog_service.list(client.ListItemsRequest())
    assert tuple(view.name for view in list_items_response.items) == ("Anvil", "Bellows")


def test_listing_an_empty_catalog_answers_nothing() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.FOUND),
        FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED, reason=""),
    )
    list_items_response = catalog_service.list(client.ListItemsRequest())
    assert list_items_response.items == ()


def test_getting_an_empty_id_is_refused_rather_than_answering_nothing() -> None:
    catalog_service = application.CatalogService(
        FakeItemRepository(outcome=ports.ItemLookup.FOUND),
        FakeNamePolicy(verdict=ports.NameVerdict.ALLOWED, reason=""),
    )
    with pytest.raises(ValueError, match="id must be non-empty"):
        catalog_service.get(client.GetItemRequest(id=""))


def test_a_found_lookup_carries_a_view_per_row() -> None:
    find_item_response = ports.FindItemResponse(
        outcome=ports.ItemLookup.FOUND,
        items=(ports.ItemView(id="a1", name="Anvil"),),
    )
    get_item_response = application.MapToGetItemResponse(
        find_item_response=find_item_response
    )
    assert tuple((view.id, view.name) for view in get_item_response.items) == (
        ("a1", "Anvil"),
    )


def test_an_archived_lookup_carries_nothing_even_though_it_carries_a_row() -> None:
    find_item_response = ports.FindItemResponse(
        outcome=ports.ItemLookup.ARCHIVED,
        items=(ports.ItemView(id="a1", name="Anvil"),),
    )
    get_item_response = application.MapToGetItemResponse(
        find_item_response=find_item_response
    )
    assert get_item_response.items == ()


def test_a_missing_lookup_carries_nothing() -> None:
    find_item_response = ports.FindItemResponse(outcome=ports.ItemLookup.MISSING, items=())
    get_item_response = application.MapToGetItemResponse(
        find_item_response=find_item_response
    )
    assert get_item_response.items == ()


def test_an_allowed_name_carries_the_item_and_the_policys_empty_reason() -> None:
    item = domain.Item(domain.ItemSpec(id="a1", name="Anvil"))
    check_name_response = ports.CheckNameResponse(verdict=ports.NameVerdict.ALLOWED, reason="")
    add_item_response = application.MapToAddItemResponse(
        item=item, check_name_response=check_name_response
    )
    assert tuple((view.id, view.name) for view in add_item_response.items) == (
        ("a1", "Anvil"),
    )
    assert add_item_response.reason == ""


def test_a_reserved_name_carries_no_item_and_the_reason_the_policy_gave() -> None:
    item = domain.Item(domain.ItemSpec(id="a1", name="admin"))
    check_name_response = ports.CheckNameResponse(
        verdict=ports.NameVerdict.RESERVED, reason="name is reserved"
    )
    add_item_response = application.MapToAddItemResponse(
        item=item, check_name_response=check_name_response
    )
    assert add_item_response.items == ()
    assert add_item_response.reason == "name is reserved"


def test_a_repository_row_becomes_the_clients_item_view() -> None:
    item_view = application.MapToItemView(
        item_view=ports.ItemView(id="a1", name="Anvil")
    )
    assert (item_view.id, item_view.name) == ("a1", "Anvil")


def test_an_added_item_becomes_the_clients_item_view() -> None:
    item = domain.Item(domain.ItemSpec(id="b2", name="Bellows"))
    item_view = application.MapToAddedItemView(item=item)
    assert (item_view.id, item_view.name) == ("b2", "Bellows")
