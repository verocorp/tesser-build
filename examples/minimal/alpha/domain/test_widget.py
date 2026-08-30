from __future__ import annotations

import pytest

import alpha.domain.clearance as clearance
import alpha.domain.widget as widget
import tesser.errors as errors


class TestWidget:

    def test_a_widget_constructs_from_its_spec(self) -> None:
        spec = widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="kept")
        built = widget.Widget(spec)
        assert str(built.identity) == spec.name

    def test_taking_a_new_part_replaces_the_held_one(self) -> None:
        built = widget.Widget(widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="kept"))
        assert built.take(widget.PartSpec(id="q")) is widget.Taken.TAKEN
        assert built.part == widget.Part(widget.PartSpec(id="q"))

    def test_taking_the_held_part_changes_nothing(self) -> None:
        built = widget.Widget(widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="kept"))
        assert built.take(widget.PartSpec(id="p")) is widget.Taken.HELD
        assert built.part == widget.Part(widget.PartSpec(id="p"))

    def test_a_widget_beta_cleared_stands_as_kept(self) -> None:
        built = widget.Widget(
            widget.WidgetSpec(name="a", part=widget.PartSpec(id="a"), standing="kept")
        )
        built.clear(clearance.ClearanceSpec(verdict="ok"))
        assert built.standing == clearance.Standing("kept")

    def test_a_widget_beta_refused_stands_as_released(self) -> None:
        built = widget.Widget(
            widget.WidgetSpec(name="a", part=widget.PartSpec(id="a"), standing="kept")
        )
        built.clear(clearance.ClearanceSpec(verdict="refused"))
        assert built.standing == clearance.Standing("released")

    def test_a_widget_rebuilds_the_standing_its_spec_carries(self) -> None:
        built = widget.Widget(
            widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="released")
        )
        assert built.standing == clearance.Standing("released")

    def test_a_standing_outside_the_set_refuses_the_widget(self) -> None:
        with pytest.raises(errors.DomainError):
            widget.Widget(
                widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="maybe")
            )
