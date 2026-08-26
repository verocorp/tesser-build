from __future__ import annotations

import pytest

import alpha.domain.state as state
import alpha.domain.thing as thing
import kernel.ident as ident
import tesser.errors as errors


def test_a_name_is_lowercase_letters() -> None:
    with pytest.raises(errors.DomainError):
        thing.Name("A1")
    assert str(thing.Name("ab")) == "ab"


def test_a_count_is_never_negative() -> None:
    with pytest.raises(errors.DomainError):
        thing.Count(-1)
    assert int(thing.Count(2)) == 2


def test_a_pair_equals_by_value() -> None:
    assert thing.Pair(thing.PairSpec("a", 1)) == thing.Pair(thing.PairSpec("a", 1))


def test_a_part_equals_by_identity() -> None:
    on = thing.Part(thing.PartSpec("p", state.State.ON))
    off = thing.Part(thing.PartSpec("p", state.State.OFF))
    assert on == off
    on.toggle()
    assert on.state is state.State.OFF


def test_a_whole_constructs_from_its_spec() -> None:
    whole = thing.Whole(
        thing.WholeSpec(
            id="w", pair=thing.PairSpec("a", 1), parts=(thing.PartSpec("p", state.State.ON),), other="o"
        )
    )
    assert whole.identity == ident.Ident("w")
    assert whole.other == ident.Ident("o")
    whole.toggle_all()
    assert tuple(part.state for part in whole.parts) == (state.State.OFF,)
