from __future__ import annotations

import pytest

import alpha.domain.clearance as clearance
import tesser.errors as errors


class TestClearance:

    def test_a_verdict_outside_the_set_is_refused(self) -> None:
        with pytest.raises(errors.DomainError):
            clearance.Clearance(clearance.ClearanceSpec(verdict="maybe"))

    def test_equality_is_by_value(self) -> None:
        one = clearance.Clearance(clearance.ClearanceSpec(verdict="ok"))
        other = clearance.Clearance(clearance.ClearanceSpec(verdict="ok"))
        assert one == other
        assert one != clearance.Clearance(clearance.ClearanceSpec(verdict="refused"))

    def test_string_is_the_canonical_exit(self) -> None:
        assert str(clearance.Clearance(clearance.ClearanceSpec(verdict="refused"))) == "refused"

    def test_an_ok_verdict_settles_as_kept(self) -> None:
        settled = clearance.Clearance(clearance.ClearanceSpec(verdict="ok")).settle()
        assert settled is clearance.Settled.KEPT

    def test_a_refused_verdict_settles_as_dropped(self) -> None:
        settled = clearance.Clearance(clearance.ClearanceSpec(verdict="refused")).settle()
        assert settled is clearance.Settled.DROPPED
