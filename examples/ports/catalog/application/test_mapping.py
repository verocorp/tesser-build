from __future__ import annotations

import catalog.application.mapping as mapping
import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.domain.item as item


def test_a_found_lookup_exposes_a_view_mapper_per_row() -> None:
    found = item_repository.FindItemResponse(
        outcome=item_repository.ItemLookup.FOUND,
        items=(item_repository.ItemView(id="a1", name="Anvil"),),
    )
    mapper = mapping.MapToGetItemResponse(found=found)
    assert tuple((m.id, m.name) for m in mapper.item_view_mappers) == (("a1", "Anvil"),)


def test_an_archived_lookup_exposes_nothing_even_though_it_carries_a_row() -> None:
    found = item_repository.FindItemResponse(
        outcome=item_repository.ItemLookup.ARCHIVED,
        items=(item_repository.ItemView(id="a1", name="Anvil"),),
    )
    mapper = mapping.MapToGetItemResponse(found=found)
    assert mapper.item_view_mappers == ()


def test_a_missing_lookup_exposes_nothing() -> None:
    found = item_repository.FindItemResponse(
        outcome=item_repository.ItemLookup.MISSING, items=()
    )
    mapper = mapping.MapToGetItemResponse(found=found)
    assert mapper.item_view_mappers == ()


def test_an_allowed_name_exposes_the_entity_and_the_policys_empty_reason() -> None:
    entity = item.Item(item.ItemSpec(id="a1", name="Anvil"))
    checked = name_policy.CheckNameResponse(
        verdict=name_policy.NameVerdict.ALLOWED, reason=""
    )
    mapper = mapping.MapToAddItemResponse(entity=entity, checked=checked)
    assert tuple((m.id, m.name) for m in mapper.item_view_mappers) == (("a1", "Anvil"),)
    assert mapper.reason == ""


def test_a_reserved_name_exposes_no_item_and_carries_the_reason_the_policy_gave() -> None:
    entity = item.Item(item.ItemSpec(id="a1", name="admin"))
    checked = name_policy.CheckNameResponse(
        verdict=name_policy.NameVerdict.RESERVED, reason="name is reserved"
    )
    mapper = mapping.MapToAddItemResponse(entity=entity, checked=checked)
    assert mapper.item_view_mappers == ()
    assert mapper.reason == "name is reserved"
