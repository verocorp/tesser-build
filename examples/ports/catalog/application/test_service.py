from __future__ import annotations

import pytest
import tesser.testing as ts

import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.application.service as service
import catalog.client.client as client


@ts.fake
class FakeItemRepository(item_repository.ItemRepository):

    def __init__(self, outcome: item_repository.ItemLookup) -> None:
        self.outcome = outcome
        self.rows: dict[str, item_repository.ItemView] = {}

    def save(self, request: item_repository.SaveItemRequest) -> item_repository.SaveItemResponse:
        self.rows[request.id] = item_repository.ItemView(id=request.id, name=request.name)
        return item_repository.SaveItemResponse()

    def find(self, request: item_repository.FindItemRequest) -> item_repository.FindItemResponse:
        row = self.rows.get(request.id)
        if row is None:
            return item_repository.FindItemResponse(
                outcome=item_repository.ItemLookup.MISSING, items=()
            )
        return item_repository.FindItemResponse(outcome=self.outcome, items=(row,))

    def all(self, request: item_repository.ListItemsRequest) -> item_repository.ListItemsResponse:
        return item_repository.ListItemsResponse(items=tuple(self.rows.values()))


@ts.fake
class FakeNamePolicy(name_policy.NamePolicy):

    def __init__(self, verdict: name_policy.NameVerdict, reason: str) -> None:
        self.verdict = verdict
        self.reason = reason
        self.asked: list[str] = []

    def check(self, request: name_policy.CheckNameRequest) -> name_policy.CheckNameResponse:
        self.asked.append(request.name)
        return name_policy.CheckNameResponse(verdict=self.verdict, reason=self.reason)


def test_adding_an_item_answers_with_what_was_stored() -> None:
    svc = service.CatalogService(
        FakeItemRepository(outcome=item_repository.ItemLookup.FOUND),
        FakeNamePolicy(verdict=name_policy.NameVerdict.ALLOWED, reason=""),
    )
    added = svc.add(client.AddItemRequest(id="a1", name="Anvil"))
    assert (added.id, added.name, added.reason) == ("a1", "Anvil", "")


def test_adding_an_item_asks_the_policy_about_the_requested_name() -> None:
    names = FakeNamePolicy(verdict=name_policy.NameVerdict.ALLOWED, reason="")
    svc = service.CatalogService(
        FakeItemRepository(outcome=item_repository.ItemLookup.FOUND), names
    )
    svc.add(client.AddItemRequest(id="a1", name="Anvil"))
    assert names.asked == ["Anvil"]


def test_a_refused_name_answers_blank_with_the_reason_the_policy_gave() -> None:
    svc = service.CatalogService(
        FakeItemRepository(outcome=item_repository.ItemLookup.FOUND),
        FakeNamePolicy(
            verdict=name_policy.NameVerdict.RESERVED, reason="name is reserved"
        ),
    )
    added = svc.add(client.AddItemRequest(id="c3", name="admin"))
    assert (added.id, added.name, added.reason) == ("", "", "name is reserved")


def test_an_item_with_no_name_is_refused_before_any_port_is_touched() -> None:
    items = FakeItemRepository(outcome=item_repository.ItemLookup.FOUND)
    names = FakeNamePolicy(verdict=name_policy.NameVerdict.ALLOWED, reason="")
    svc = service.CatalogService(items, names)
    with pytest.raises(ValueError, match="name must be non-empty"):
        svc.add(client.AddItemRequest(id="a1", name=""))
    assert items.rows == {}
    assert names.asked == []


def test_getting_an_added_item_answers_it() -> None:
    svc = service.CatalogService(
        FakeItemRepository(outcome=item_repository.ItemLookup.FOUND),
        FakeNamePolicy(verdict=name_policy.NameVerdict.ALLOWED, reason=""),
    )
    svc.add(client.AddItemRequest(id="a1", name="Anvil"))
    got = svc.get(client.GetItemRequest(id="a1"))
    assert tuple((view.id, view.name) for view in got.items) == (("a1", "Anvil"),)


def test_getting_an_id_that_was_never_added_answers_nothing() -> None:
    svc = service.CatalogService(
        FakeItemRepository(outcome=item_repository.ItemLookup.FOUND),
        FakeNamePolicy(verdict=name_policy.NameVerdict.ALLOWED, reason=""),
    )
    got = svc.get(client.GetItemRequest(id="ghost"))
    assert got.items == ()


def test_an_archived_item_is_not_served_as_live() -> None:
    svc = service.CatalogService(
        FakeItemRepository(outcome=item_repository.ItemLookup.ARCHIVED),
        FakeNamePolicy(verdict=name_policy.NameVerdict.ALLOWED, reason=""),
    )
    svc.add(client.AddItemRequest(id="b2", name="Bellows"))
    got = svc.get(client.GetItemRequest(id="b2"))
    assert got.items == ()


def test_listing_answers_every_added_item() -> None:
    svc = service.CatalogService(
        FakeItemRepository(outcome=item_repository.ItemLookup.FOUND),
        FakeNamePolicy(verdict=name_policy.NameVerdict.ALLOWED, reason=""),
    )
    svc.add(client.AddItemRequest(id="a1", name="Anvil"))
    svc.add(client.AddItemRequest(id="b2", name="Bellows"))
    listed = svc.list(client.ListItemsRequest())
    assert tuple(view.name for view in listed.items) == ("Anvil", "Bellows")


def test_listing_an_empty_catalog_answers_nothing() -> None:
    svc = service.CatalogService(
        FakeItemRepository(outcome=item_repository.ItemLookup.FOUND),
        FakeNamePolicy(verdict=name_policy.NameVerdict.ALLOWED, reason=""),
    )
    listed = svc.list(client.ListItemsRequest())
    assert listed.items == ()
