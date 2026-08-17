from __future__ import annotations

import tesser.testing as ts

import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.application.service as service
import catalog.client.client as client
import catalog.component.component as wire


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

    def __init__(self, verdict: name_policy.NameVerdict) -> None:
        self.verdict = verdict

    def check(self, request: name_policy.CheckNameRequest) -> name_policy.CheckNameResponse:
        return name_policy.CheckNameResponse(verdict=self.verdict, reason="fixed")


def test_add_then_get_returns_the_item() -> None:
    svc = wire.Catalog().client
    svc.add(client.AddItemRequest(id="a1", name="Anvil"))
    got = svc.get(client.GetItemRequest(id="a1"))
    assert tuple((v.id, v.name) for v in got.items) == (("a1", "Anvil"),)


def test_get_of_an_unknown_item_answers_empty() -> None:
    svc = wire.Catalog().client
    got = svc.get(client.GetItemRequest(id="nope"))
    assert got.items == ()


def test_an_archived_item_is_not_served_as_live() -> None:
    svc = service.CatalogService(
        FakeItemRepository(outcome=item_repository.ItemLookup.ARCHIVED),
        FakeNamePolicy(verdict=name_policy.NameVerdict.ALLOWED),
    )
    svc.add(client.AddItemRequest(id="b2", name="Bellows"))
    got = svc.get(client.GetItemRequest(id="b2"))
    assert got.items == ()


def test_a_reserved_name_is_refused_with_a_reason() -> None:
    svc = wire.Catalog().client
    added = svc.add(client.AddItemRequest(id="c3", name="admin"))
    assert (added.id, added.reason) == ("", "name is reserved")


def test_list_returns_every_stored_item() -> None:
    svc = wire.Catalog().client
    svc.add(client.AddItemRequest(id="d4", name="Drill"))
    listed = svc.list(client.ListItemsRequest())
    assert tuple(v.name for v in listed.items) == ("Drill",)
