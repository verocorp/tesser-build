from __future__ import annotations

import alpha.domain.clearance as clearance
import alpha.domain.widget as widget


class TestWidget:

    def test_a_widget_constructs_from_its_spec(self) -> None:
        spec = widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"))
        built = widget.Widget(spec)
        assert str(built.identity) == spec.name

    def test_taking_a_new_part_replaces_the_held_one(self) -> None:
        built = widget.Widget(widget.WidgetSpec(name="a", part=widget.PartSpec(id="p")))
        assert built.take(widget.PartSpec(id="q")) is widget.Taken.TAKEN
        assert built.part == widget.Part(widget.PartSpec(id="q"))

    def test_taking_the_held_part_changes_nothing(self) -> None:
        built = widget.Widget(widget.WidgetSpec(name="a", part=widget.PartSpec(id="p")))
        assert built.take(widget.PartSpec(id="p")) is widget.Taken.HELD
        assert built.part == widget.Part(widget.PartSpec(id="p"))

    def test_a_widget_beta_cleared_keeps_the_part_it_holds(self) -> None:
        built = widget.Widget(widget.WidgetSpec(name="a", part=widget.PartSpec(id="a")))
        cleared = built.clear(clearance.ClearanceSpec(verdict="ok"))
        assert cleared is widget.Cleared.KEPT

    def test_a_widget_beta_refused_releases_the_part_it_holds(self) -> None:
        built = widget.Widget(widget.WidgetSpec(name="a", part=widget.PartSpec(id="a")))
        cleared = built.clear(clearance.ClearanceSpec(verdict="refused"))
        assert cleared is widget.Cleared.RELEASED
