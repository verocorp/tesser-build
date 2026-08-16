from __future__ import annotations

import pytest

import catalog.application.mapping as mapping
import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.domain.item as item


def test_a_save_request_carries_the_entity_id_and_name() -> None:
    entity = item.Item(item.ItemSpec(id="a1", name="Anvil"))
    request = mapping.save_request(entity)
    assert (request.id, request.name) == ("a1", "Anvil")


def test_a_spec_is_built_from_a_stored_view() -> None:
    spec = mapping.item_spec(item_repository.ItemView(id="a1", name="Anvil"))
    assert (spec.id, spec.name) == ("a1", "Anvil")


def test_an_item_is_rebuilt_from_a_stored_view() -> None:
    entity = mapping.rebuilt(item_repository.ItemView(id="a1", name="Anvil"))
    assert (entity.id(), entity.name()) == ("a1", "Anvil")


def test_rebuilding_a_view_with_no_name_is_refused() -> None:
    with pytest.raises(ValueError, match="name must be non-empty"):
        mapping.rebuilt(item_repository.ItemView(id="a1", name=""))


def test_a_found_lookup_becomes_the_client_views() -> None:
    found = item_repository.FindItemResponse(
        outcome=item_repository.ItemLookup.FOUND,
        items=(item_repository.ItemView(id="a1", name="Anvil"),),
    )
    response = mapping.get_response(found)
    assert tuple((view.id, view.name) for view in response.items) == (("a1", "Anvil"),)


def test_an_archived_lookup_answers_nothing_even_though_it_carries_a_row() -> None:
    found = item_repository.FindItemResponse(
        outcome=item_repository.ItemLookup.ARCHIVED,
        items=(item_repository.ItemView(id="a1", name="Anvil"),),
    )
    response = mapping.get_response(found)
    assert response.items == ()


def test_a_missing_lookup_answers_nothing() -> None:
    found = item_repository.FindItemResponse(
        outcome=item_repository.ItemLookup.MISSING, items=()
    )
    response = mapping.get_response(found)
    assert response.items == ()


def test_a_listing_maps_every_stored_view_in_order() -> None:
    listed = item_repository.ListItemsResponse(
        items=(
            item_repository.ItemView(id="a1", name="Anvil"),
            item_repository.ItemView(id="b2", name="Bellows"),
        )
    )
    response = mapping.list_response(listed)
    assert tuple((view.id, view.name) for view in response.items) == (
        ("a1", "Anvil"),
        ("b2", "Bellows"),
    )


def test_an_empty_listing_answers_nothing() -> None:
    response = mapping.list_response(item_repository.ListItemsResponse(items=()))
    assert response.items == ()


def test_an_allowed_name_answers_the_entity_with_no_reason() -> None:
    entity = item.Item(item.ItemSpec(id="a1", name="Anvil"))
    checked = name_policy.CheckNameResponse(
        verdict=name_policy.NameVerdict.ALLOWED, reason=""
    )
    response = mapping.add_response(entity, checked)
    assert (response.id, response.name, response.reason) == ("a1", "Anvil", "")


def test_a_reserved_name_answers_blank_with_the_reason_the_policy_gave() -> None:
    entity = item.Item(item.ItemSpec(id="a1", name="admin"))
    checked = name_policy.CheckNameResponse(
        verdict=name_policy.NameVerdict.RESERVED, reason="name is reserved"
    )
    response = mapping.add_response(entity, checked)
    assert (response.id, response.name, response.reason) == ("", "", "name is reserved")
