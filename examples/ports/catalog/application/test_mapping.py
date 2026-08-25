from __future__ import annotations

import catalog.application.mapping as mapping
import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.domain.item as item


def test_a_found_lookup_carries_a_view_per_row() -> None:
    found = item_repository.FindItemResponse(
        outcome=item_repository.ItemLookup.FOUND,
        items=(item_repository.ItemView(id="a1", name="Anvil"),),
    )
    response = mapping.MapToGetItemResponse(found=found)
    assert tuple((view.id, view.name) for view in response.items) == (("a1", "Anvil"),)


def test_an_archived_lookup_carries_nothing_even_though_it_carries_a_row() -> None:
    found = item_repository.FindItemResponse(
        outcome=item_repository.ItemLookup.ARCHIVED,
        items=(item_repository.ItemView(id="a1", name="Anvil"),),
    )
    response = mapping.MapToGetItemResponse(found=found)
    assert response.items == ()


def test_a_missing_lookup_carries_nothing() -> None:
    found = item_repository.FindItemResponse(
        outcome=item_repository.ItemLookup.MISSING, items=()
    )
    response = mapping.MapToGetItemResponse(found=found)
    assert response.items == ()


def test_an_allowed_name_carries_the_entity_and_the_policys_empty_reason() -> None:
    entity = item.Item(item.ItemSpec(id="a1", name="Anvil"))
    checked = name_policy.CheckNameResponse(
        verdict=name_policy.NameVerdict.ALLOWED, reason=""
    )
    response = mapping.MapToAddItemResponse(entity=entity, checked=checked)
    assert tuple((view.id, view.name) for view in response.items) == (("a1", "Anvil"),)
    assert response.reason == ""


def test_a_reserved_name_carries_no_item_and_the_reason_the_policy_gave() -> None:
    entity = item.Item(item.ItemSpec(id="a1", name="admin"))
    checked = name_policy.CheckNameResponse(
        verdict=name_policy.NameVerdict.RESERVED, reason="name is reserved"
    )
    response = mapping.MapToAddItemResponse(entity=entity, checked=checked)
    assert response.items == ()
    assert response.reason == "name is reserved"


def test_a_repository_row_becomes_the_clients_item_view() -> None:
    view = mapping.MapToItemView(view=item_repository.ItemView(id="a1", name="Anvil"))
    assert (view.id, view.name) == ("a1", "Anvil")


def test_an_added_entity_becomes_the_clients_item_view() -> None:
    entity = item.Item(item.ItemSpec(id="b2", name="Bellows"))
    view = mapping.MapToAddedItemView(entity=entity)
    assert (view.id, view.name) == ("b2", "Bellows")
