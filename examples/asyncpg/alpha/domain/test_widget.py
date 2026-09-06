from __future__ import annotations

import pytest

import alpha.domain as domain
import tesser.errors as errors


class TestWidget:

    def test_a_widget_constructs_from_its_spec(self) -> None:
        widget_spec = domain.WidgetSpec(name="a", part=domain.PartSpec(id="p"), standing="kept")
        widget = domain.Widget(widget_spec)
        assert str(widget.identity) == widget_spec.name

    def test_taking_a_new_part_replaces_the_held_one(self) -> None:
        widget = domain.Widget(
            domain.WidgetSpec(name="a", part=domain.PartSpec(id="p"), standing="kept")
        )
        assert widget.take(domain.PartSpec(id="q")) is domain.Taken.TAKEN
        assert str(widget.part.identity) == "q"

    def test_taking_the_held_part_changes_nothing(self) -> None:
        widget = domain.Widget(
            domain.WidgetSpec(name="a", part=domain.PartSpec(id="p"), standing="kept")
        )
        assert widget.take(domain.PartSpec(id="p")) is domain.Taken.HELD
        assert str(widget.part.identity) == "p"

    def test_a_widget_beta_cleared_stands_as_kept(self) -> None:
        widget = domain.Widget(
            domain.WidgetSpec(name="a", part=domain.PartSpec(id="a"), standing="kept")
        )
        widget.clear(domain.ClearanceSpec(verdict="ok"))
        assert str(widget.standing) == "kept"

    def test_a_widget_beta_refused_stands_as_released(self) -> None:
        widget = domain.Widget(
            domain.WidgetSpec(name="a", part=domain.PartSpec(id="a"), standing="kept")
        )
        widget.clear(domain.ClearanceSpec(verdict="refused"))
        assert str(widget.standing) == "released"

    def test_a_released_widget_beta_later_clears_stands_as_kept_again(self) -> None:
        widget = domain.Widget(
            domain.WidgetSpec(name="a", part=domain.PartSpec(id="a"), standing="released")
        )
        widget.clear(domain.ClearanceSpec(verdict="ok"))
        assert str(widget.standing) == "kept"

    def test_a_verdict_outside_the_set_refuses_the_clearance(self) -> None:
        widget = domain.Widget(
            domain.WidgetSpec(name="a", part=domain.PartSpec(id="a"), standing="kept")
        )
        with pytest.raises(errors.DomainError):
            widget.clear(domain.ClearanceSpec(verdict="maybe"))

    def test_a_widget_rebuilds_the_standing_its_spec_carries(self) -> None:
        widget = domain.Widget(
            domain.WidgetSpec(name="a", part=domain.PartSpec(id="p"), standing="released")
        )
        assert str(widget.standing) == "released"

    def test_a_standing_outside_the_set_refuses_the_widget(self) -> None:
        with pytest.raises(errors.DomainError):
            domain.Widget(
                domain.WidgetSpec(name="a", part=domain.PartSpec(id="p"), standing="maybe")
            )

    def test_an_empty_name_refuses_the_widget(self) -> None:
        with pytest.raises(errors.DomainError):
            domain.Widget(
                domain.WidgetSpec(name="", part=domain.PartSpec(id="p"), standing="kept")
            )


class TestName:

    def test_a_name_equals_by_value(self) -> None:
        first = domain.Name("a")
        second = domain.Name("a")
        assert first == second
        assert first != domain.Name("b")

    def test_string_is_the_canonical_exit(self) -> None:
        assert str(domain.Name("a")) == "a"
