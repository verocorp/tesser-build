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

    def test_an_ok_verdict_decides_cleared(self) -> None:
        assert (
            clearance.Clearance(clearance.ClearanceSpec(verdict="ok")).decide()
            is clearance.Verdict.CLEARED
        )

    def test_a_refused_verdict_decides_refused(self) -> None:
        assert (
            clearance.Clearance(clearance.ClearanceSpec(verdict="refused")).decide()
            is clearance.Verdict.REFUSED
        )


class TestStanding:

    def test_a_standing_outside_the_set_is_refused(self) -> None:
        with pytest.raises(errors.DomainError):
            clearance.Standing("maybe")

    def test_equality_is_by_value(self) -> None:
        assert clearance.Standing("kept") == clearance.Standing("kept")
        assert clearance.Standing("kept") != clearance.Standing("released")

    def test_string_is_the_canonical_exit(self) -> None:
        assert str(clearance.Standing("released")) == "released"
