from __future__ import annotations

import pytest

import alpha.domain.clearance as clearance
import alpha.domain.widget as widget
import tesser.errors as errors


class TestWidget:

    def test_a_widget_constructs_from_its_spec(self) -> None:
        widget_spec = widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="kept")
        domain_widget = widget.Widget(widget_spec)
        assert str(domain_widget.identity) == widget_spec.name

    def test_taking_a_new_part_replaces_the_held_one(self) -> None:
        domain_widget = widget.Widget(widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="kept"))
        assert domain_widget.take(widget.PartSpec(id="q")) is widget.Taken.TAKEN
        assert domain_widget.part == widget.Part(widget.PartSpec(id="q"))

    def test_taking_the_held_part_changes_nothing(self) -> None:
        domain_widget = widget.Widget(widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="kept"))
        assert domain_widget.take(widget.PartSpec(id="p")) is widget.Taken.HELD
        assert domain_widget.part == widget.Part(widget.PartSpec(id="p"))

    def test_a_widget_beta_cleared_stands_as_kept(self) -> None:
        domain_widget = widget.Widget(
            widget.WidgetSpec(name="a", part=widget.PartSpec(id="a"), standing="kept")
        )
        domain_widget.clear(clearance.ClearanceSpec(verdict="ok"))
        assert domain_widget.standing == clearance.Standing("kept")

    def test_a_widget_beta_refused_stands_as_released(self) -> None:
        domain_widget = widget.Widget(
            widget.WidgetSpec(name="a", part=widget.PartSpec(id="a"), standing="kept")
        )
        domain_widget.clear(clearance.ClearanceSpec(verdict="refused"))
        assert domain_widget.standing == clearance.Standing("released")

    def test_a_widget_rebuilds_the_standing_its_spec_carries(self) -> None:
        domain_widget = widget.Widget(
            widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="released")
        )
        assert domain_widget.standing == clearance.Standing("released")

    def test_a_standing_outside_the_set_refuses_the_widget(self) -> None:
        with pytest.raises(errors.DomainError):
            widget.Widget(
                widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="maybe")
            )
