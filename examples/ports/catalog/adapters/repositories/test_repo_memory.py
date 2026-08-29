from __future__ import annotations

import typing

import catalog.adapters.repositories.repo_memory as repo_memory
import catalog.application.ports.item_repository as item_repository


def test_a_saved_item_is_found_by_its_id() -> None:
    repo = repo_memory.MemoryItemRepository()
    repo.save(item_repository.SaveItemRequest(id="a1", name="Anvil"))
    found = repo.find(item_repository.FindItemRequest(id="a1"))
    match found.outcome:
        case item_repository.ItemLookup.FOUND:
            assert tuple((view.id, view.name) for view in found.items) == (("a1", "Anvil"),)
        case item_repository.ItemLookup.ARCHIVED | item_repository.ItemLookup.MISSING:
            raise AssertionError("a saved item is served as found")
        case _ as unreachable:
            typing.assert_never(unreachable)


def test_an_id_that_was_never_saved_is_missing_and_carries_nothing() -> None:
    repo = repo_memory.MemoryItemRepository()
    found = repo.find(item_repository.FindItemRequest(id="ghost"))
    assert (found.outcome, found.items) == (item_repository.ItemLookup.MISSING, ())


def test_saving_an_id_again_replaces_the_stored_name() -> None:
    repo = repo_memory.MemoryItemRepository()
    repo.save(item_repository.SaveItemRequest(id="a1", name="Anvil"))
    repo.save(item_repository.SaveItemRequest(id="a1", name="Anvil Mk II"))
    found = repo.find(item_repository.FindItemRequest(id="a1"))
    listed = repo.all(item_repository.ListItemsRequest())
    assert tuple(view.name for view in found.items) == ("Anvil Mk II",)
    assert len(listed.items) == 1


def test_all_answers_every_saved_item_in_the_order_they_were_saved() -> None:
    repo = repo_memory.MemoryItemRepository()
    repo.save(item_repository.SaveItemRequest(id="a1", name="Anvil"))
    repo.save(item_repository.SaveItemRequest(id="b2", name="Bellows"))
    listed = repo.all(item_repository.ListItemsRequest())
    assert tuple((view.id, view.name) for view in listed.items) == (
        ("a1", "Anvil"),
        ("b2", "Bellows"),
    )


def test_a_fresh_repository_answers_nothing() -> None:
    repo = repo_memory.MemoryItemRepository()
    listed = repo.all(item_repository.ListItemsRequest())
    assert listed.items == ()


def test_two_repositories_do_not_share_their_rows() -> None:
    first = repo_memory.MemoryItemRepository()
    second = repo_memory.MemoryItemRepository()
    first.save(item_repository.SaveItemRequest(id="a1", name="Anvil"))
    found = second.find(item_repository.FindItemRequest(id="a1"))
    assert found.outcome is item_repository.ItemLookup.MISSING
