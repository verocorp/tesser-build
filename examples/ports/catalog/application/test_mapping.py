from __future__ import annotations

import catalog.application.mapping as mapping
import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.domain.item as item


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
