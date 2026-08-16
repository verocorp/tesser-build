from __future__ import annotations

import pytest

import catalog.domain.item as item


def test_an_item_carries_the_id_and_name_from_its_spec() -> None:
    entity = item.Item(item.ItemSpec(id="a1", name="Anvil"))
    assert (entity.id(), entity.name()) == ("a1", "Anvil")


def test_a_name_is_kept_exactly_as_it_was_given() -> None:
    entity = item.Item(item.ItemSpec(id=" a1 ", name="  Anvil  "))
    assert (entity.id(), entity.name()) == (" a1 ", "  Anvil  ")


def test_an_item_without_an_id_is_refused() -> None:
    with pytest.raises(ValueError, match="id must be non-empty"):
        item.Item(item.ItemSpec(id="", name="Anvil"))


def test_an_item_without_a_name_is_refused() -> None:
    with pytest.raises(ValueError, match="name must be non-empty"):
        item.Item(item.ItemSpec(id="a1", name=""))


def test_a_wholly_empty_spec_is_refused_for_its_id() -> None:
    with pytest.raises(ValueError, match="id must be non-empty"):
        item.Item(item.ItemSpec(id="", name=""))
