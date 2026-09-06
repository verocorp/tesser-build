from __future__ import annotations

import typing

import catalog.adapters.repositories as repositories
import catalog.application.ports as ports


def test_a_saved_item_is_found_by_its_id() -> None:
    memory_item_repository = repositories.MemoryItemRepository()
    memory_item_repository.save(ports.SaveItemRequest(id="a1", name="Anvil"))
    find_item_response = memory_item_repository.find(ports.FindItemRequest(id="a1"))
    match find_item_response.outcome:
        case ports.ItemLookup.FOUND:
            assert tuple(
                (view.id, view.name) for view in find_item_response.items
            ) == (("a1", "Anvil"),)
        case ports.ItemLookup.ARCHIVED | ports.ItemLookup.MISSING:
            raise AssertionError("a saved item is served as found")
        case _ as unreachable:
            typing.assert_never(unreachable)


def test_an_id_that_was_never_saved_is_missing_and_carries_nothing() -> None:
    memory_item_repository = repositories.MemoryItemRepository()
    find_item_response = memory_item_repository.find(ports.FindItemRequest(id="ghost"))
    assert (find_item_response.outcome, find_item_response.items) == (
        ports.ItemLookup.MISSING,
        (),
    )


def test_saving_an_id_again_replaces_the_stored_name() -> None:
    memory_item_repository = repositories.MemoryItemRepository()
    memory_item_repository.save(ports.SaveItemRequest(id="a1", name="Anvil"))
    memory_item_repository.save(ports.SaveItemRequest(id="a1", name="Anvil Mk II"))
    find_item_response = memory_item_repository.find(ports.FindItemRequest(id="a1"))
    list_items_response = memory_item_repository.all(ports.ListItemsRequest())
    assert tuple(view.name for view in find_item_response.items) == ("Anvil Mk II",)
    assert len(list_items_response.items) == 1


def test_all_answers_every_saved_item_in_the_order_they_were_saved() -> None:
    memory_item_repository = repositories.MemoryItemRepository()
    memory_item_repository.save(ports.SaveItemRequest(id="a1", name="Anvil"))
    memory_item_repository.save(ports.SaveItemRequest(id="b2", name="Bellows"))
    list_items_response = memory_item_repository.all(ports.ListItemsRequest())
    assert tuple((view.id, view.name) for view in list_items_response.items) == (
        ("a1", "Anvil"),
        ("b2", "Bellows"),
    )


def test_a_fresh_repository_answers_nothing() -> None:
    memory_item_repository = repositories.MemoryItemRepository()
    list_items_response = memory_item_repository.all(ports.ListItemsRequest())
    assert list_items_response.items == ()


def test_two_repositories_do_not_share_their_rows() -> None:
    first = repositories.MemoryItemRepository()
    second = repositories.MemoryItemRepository()
    first.save(ports.SaveItemRequest(id="a1", name="Anvil"))
    find_item_response = second.find(ports.FindItemRequest(id="a1"))
    assert find_item_response.outcome is ports.ItemLookup.MISSING
