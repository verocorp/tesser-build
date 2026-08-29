import enum
import functools
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


def test_an_outcome_member_carries_no_hand_picked_int() -> None:
    with pytest.raises(TypeError, match=r"Picked.DONE carries a value"):

        class Picked(ts.Outcome):
            DONE = 5

    with pytest.raises(TypeError, match=r"Counted.CONTINUE carries a value"):

        class Counted(ts.Outcome):
            CONTINUE = 1
            DONE = 2

    with pytest.raises(TypeError, match=r"Truthy.DONE carries a value"):

        class Truthy(ts.Outcome):
            DONE = True


def test_an_outcome_admits_no_custom_metaclass() -> None:
    class Sneaky(enum.EnumMeta):
        def sneaky(cls) -> bool:
            return True

    with pytest.raises(TypeError, match=r"Hidden uses a custom metaclass"):

        class Hidden(ts.Outcome, metaclass=Sneaky):
            DONE = enum.auto()


def test_an_outcome_hides_no_behavior_behind_an_underscore() -> None:
    with pytest.raises(TypeError, match=r"defines '_helper'"):

        class Sneaky(ts.Outcome):
            DONE = enum.auto()

            def _helper(self) -> bool:
                return True

    with pytest.raises(TypeError, match=r"defines '_make'"):

        class Crafty(ts.Outcome):
            DONE = enum.auto()

            @classmethod
            def _make(cls) -> bool:
                return True

    with pytest.raises(TypeError, match=r"defines '__bool__'"):

        class Falsy(ts.Outcome):
            DONE = enum.auto()

            def __bool__(self) -> bool:
                return False

    with pytest.raises(TypeError, match=r"defines '__str__'"):

        class Wired(ts.Outcome):
            DONE = enum.auto()

            def __str__(self) -> str:
                return "done"


def test_an_outcome_subclasses_outcome_directly_and_alone() -> None:
    with pytest.raises(TypeError, match=r"Mixed subclasses int, Outcome"):

        class Mixed(int, ts.Outcome):
            DONE = enum.auto()

    class Base(ts.Outcome):
        pass

    with pytest.raises(TypeError, match=r"Derived subclasses Base"):

        class Derived(Base):
            DONE = enum.auto()


def test_an_outcome_carries_nothing_to_read() -> None:
    with pytest.raises(TypeError, match=r"Advance is matched, never read: an outcome carries no value"):
        Advance.DONE.value
    with pytest.raises(TypeError, match=r"Advance is matched, never read: an outcome carries no name"):
        Advance.DONE.name
    assert repr(Advance.DONE) == "<Advance.DONE: 2>"
    assert Advance.DONE is Advance.DONE
    assert len({Advance.CONTINUE, Advance.DONE}) == 2


def test_an_outcome_hides_no_behavior_in_the_enum_slots() -> None:
    with pytest.raises(TypeError, match=r"Made defines '__new__'"):

        class Made(ts.Outcome):
            def __new__(cls, value: int) -> "Made":
                made = object.__new__(cls)
                made._value_ = value
                return made

            DONE = enum.auto()

    with pytest.raises(TypeError, match=r"Counted defines '_generate_next_value_'"):

        class Counted(ts.Outcome):
            @staticmethod
            def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
                return count + 1

            DONE = enum.auto()


def test_an_outcome_hides_no_behavior_behind_a_descriptor() -> None:
    with pytest.raises(TypeError, match=r"Cached defines 'is_done'"):

        class Cached(ts.Outcome):
            DONE = enum.auto()

            @functools.cached_property
            def is_done(self) -> bool:
                return self is Cached.DONE

    class Answering:
        def __get__(self, instance: object, owner: type | None = None) -> bool:
            return True

    with pytest.raises(TypeError, match=r"Described defines 'is_done'"):

        class Described(ts.Outcome):
            DONE = enum.auto()

            is_done = Answering()


def test_an_outcome_carries_nothing_but_its_members() -> None:
    with pytest.raises(TypeError, match=r"Slotted defines '__slots__'"):

        class Slotted(ts.Outcome):
            __slots__ = ()

            DONE = enum.auto()

    with pytest.raises(TypeError, match=r"Annotated defines '__annotations__'"):

        class Annotated(ts.Outcome):
            DONE = enum.auto()

            attempts: int


def test_an_outcome_member_is_never_an_alias() -> None:
    with pytest.raises(TypeError, match=r"Forged.CONTINUE repeats Forged.DONE"):

        class Forged(ts.Outcome):
            DONE = ts.Outcome._generate_next_value_("DONE", 1, 0, [])
            CONTINUE = ts.Outcome._generate_next_value_("CONTINUE", 1, 0, [])

    assert len({Advance.CONTINUE, Advance.DONE}) == 2
    assert list(Advance) == [Advance.CONTINUE, Advance.DONE]


def test_a_well_formed_outcome_survives_the_gate() -> None:
    class Settle(ts.Outcome):
        PAID = enum.auto()
        REFUSED = enum.auto()
        RETRY = enum.auto()

    def route(outcome: Settle) -> str:
        match outcome:
            case Settle.PAID:
                return "paid"
            case Settle.REFUSED:
                return "refused"
            case Settle.RETRY:
                return "retry"
            case _ as never:
                typing.assert_never(never)

    assert [route(member) for member in Settle] == ["paid", "refused", "retry"]
    assert len({Settle.PAID, Settle.REFUSED, Settle.RETRY}) == 3
