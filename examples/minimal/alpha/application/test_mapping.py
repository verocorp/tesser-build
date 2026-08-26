from __future__ import annotations

import alpha.application.mapping as mapping
import alpha.domain.thing as thing


def test_a_thing_maps_to_its_name() -> None:
    added = thing.Thing(thing.ThingSpec(name="a", part=thing.PartSpec(id="p")))
    assert mapping.MapToAddResponse(added=added).name == "a"
