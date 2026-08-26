import enum
import typing

import pytest

import tesser.domain as ts


class Advance(ts.Outcome):
    CONTINUE = enum.auto()
    DONE = enum.auto()


def test_an_outcome_is_a_closed_set_the_type_checker_can_exhaust() -> None:
    def route(outcome: Advance) -> str:
        match outcome:
            case Advance.CONTINUE:
                return "again"
            case Advance.DONE:
                return "stop"
            case _ as never:
                typing.assert_never(never)

    assert route(Advance.CONTINUE) == "again"
    assert route(Advance.DONE) == "stop"
    assert list(Advance) == [Advance.CONTINUE, Advance.DONE]


def test_an_outcome_cannot_be_extended() -> None:
    with pytest.raises(TypeError):

        class Wider(Advance):  # type: ignore[misc]
            BLOCKED = enum.auto()


def test_an_outcome_carries_no_behavior() -> None:
    with pytest.raises(TypeError, match=r"defines 'is_done'"):

        class Chatty(ts.Outcome):
            DONE = enum.auto()

            def is_done(self) -> bool:
                return True


def test_an_outcome_member_carries_no_value() -> None:
    with pytest.raises(TypeError, match=r"Named.DONE carries a value"):

        class Named(ts.Outcome):
            DONE = "done"
