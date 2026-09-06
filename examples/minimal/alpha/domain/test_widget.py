from __future__ import annotations

import pytest

import alpha.domain.widget as widget
import tesser.errors as errors


class TestClearance:

    def test_a_verdict_outside_the_set_is_refused(self) -> None:
        with pytest.raises(errors.DomainError):
            widget.Clearance(widget.ClearanceSpec(verdict="maybe"))

    def test_equality_is_by_value(self) -> None:
        first = widget.Clearance(widget.ClearanceSpec(verdict="ok"))
        second = widget.Clearance(widget.ClearanceSpec(verdict="ok"))
        assert first == second
        assert first != widget.Clearance(widget.ClearanceSpec(verdict="refused"))

    def test_string_is_the_canonical_exit(self) -> None:
        assert str(widget.Clearance(widget.ClearanceSpec(verdict="refused"))) == "refused"

    def test_an_ok_verdict_decides_cleared(self) -> None:
        assert (
            widget.Clearance(widget.ClearanceSpec(verdict="ok")).decide()
            is widget.Verdict.CLEARED
        )

    def test_a_refused_verdict_decides_refused(self) -> None:
        assert (
            widget.Clearance(widget.ClearanceSpec(verdict="refused")).decide()
            is widget.Verdict.REFUSED
        )


class TestStanding:

    def test_a_standing_outside_the_set_is_refused(self) -> None:
        with pytest.raises(errors.DomainError):
            widget.Standing("maybe")

    def test_equality_is_by_value(self) -> None:
        assert widget.Standing("kept") == widget.Standing("kept")
        assert widget.Standing("kept") != widget.Standing("released")

    def test_string_is_the_canonical_exit(self) -> None:
        assert str(widget.Standing("released")) == "released"


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
        domain_widget.clear(widget.ClearanceSpec(verdict="ok"))
        assert domain_widget.standing == widget.Standing("kept")

    def test_a_widget_beta_refused_stands_as_released(self) -> None:
        domain_widget = widget.Widget(
            widget.WidgetSpec(name="a", part=widget.PartSpec(id="a"), standing="kept")
        )
        domain_widget.clear(widget.ClearanceSpec(verdict="refused"))
        assert domain_widget.standing == widget.Standing("released")

    def test_a_widget_rebuilds_the_standing_its_spec_carries(self) -> None:
        domain_widget = widget.Widget(
            widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="released")
        )
        assert domain_widget.standing == widget.Standing("released")

    def test_a_standing_outside_the_set_refuses_the_widget(self) -> None:
        with pytest.raises(errors.DomainError):
            widget.Widget(
                widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"), standing="maybe")
            )
