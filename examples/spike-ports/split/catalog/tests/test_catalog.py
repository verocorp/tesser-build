from __future__ import annotations

import pytest

import tesser.testing as ts

import catalog.adapters.gateways.repo_memory as repo_memory
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

    def exists(
        self, request: item_repository.ItemExistsRequest
    ) -> item_repository.ItemExistsResponse:
        return item_repository.ItemExistsResponse(exists=request.id in self.rows)

    def get(self, request: item_repository.GetItemRequest) -> item_repository.GetItemResponse:
        row = self.rows.get(request.id)
        if row is None:
            # Mirrors the real adapter's contract: get() is only legal once
            # exists() has said True for this id.
            raise item_repository.ItemNotFoundError(request.id)
        return item_repository.GetItemResponse(id=row.id, name=row.name)

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


def test_port_get_of_a_missing_id_is_a_contract_violation_and_raises() -> None:
    # This is the documented answer to "what does get() do for an absent
    # item": it raises, rather than returning a hollow/zero-valued response.
    # The service always guards get() behind exists(), so this path is never
    # exercised through the client — it is only reachable by calling the
    # port directly, which is exactly the misuse the contract forbids.
    repo = repo_memory.MemoryItemRepository()
    with pytest.raises(item_repository.ItemNotFoundError):
        repo.get(item_repository.GetItemRequest(id="ghost"))


def test_fake_get_of_a_missing_id_matches_the_real_adapter() -> None:
    fake = FakeItemRepository()
    with pytest.raises(item_repository.ItemNotFoundError):
        fake.get(item_repository.GetItemRequest(id="ghost"))
