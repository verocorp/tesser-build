from __future__ import annotations

import pytest

import alpha.domain.thing as thing
import kernel.ident as ident
import tesser.errors as errors


def test_a_name_is_never_empty() -> None:
    with pytest.raises(errors.DomainError):
        thing.Name("")


def test_a_thing_constructs_from_its_spec() -> None:
    built = thing.Thing(thing.ThingSpec(name="a", part=thing.PartSpec(id="p")))
    assert built.identity == thing.Name("a")
    assert built.part.identity == ident.Ident("p")
