from __future__ import annotations

import alpha.domain.thing as thing


def test_a_thing_constructs_from_its_spec() -> None:
    assert thing.Thing(thing.ThingSpec(name="a", part=thing.PartSpec(id="p"))).identity == thing.Name("a")
