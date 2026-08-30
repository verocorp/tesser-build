from __future__ import annotations

import enum
import functools
import typing

import pytest

import tesser.domain as ts
import tesser.domain.outcome as outcome


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
    class Sneaky(outcome._OutcomeMeta):
        def sneaky(cls) -> bool:
            return True

    with pytest.raises(TypeError, match=r"Hidden uses a custom metaclass"):

        class Hidden(ts.Outcome, metaclass=Sneaky):
            DONE = enum.auto()

    class Unrelated(enum.EnumMeta):
        def unrelated(cls) -> bool:
            return True

    with pytest.raises(TypeError, match=r"metaclass conflict"):

        class Alien(ts.Outcome, metaclass=Unrelated):  # type: ignore[metaclass]
            DONE = enum.auto()


def test_a_metaclass_cannot_skip_the_gate_it_inherits() -> None:
    class Skipping(outcome._OutcomeMeta):
        def __new__(
            metacls,
            cls: str,
            bases: tuple[type, ...],
            classdict: enum._EnumDict,
            **kwargs: typing.Any,
        ) -> Skipping:
            return enum.EnumMeta.__new__(metacls, cls, bases, classdict, **kwargs)

    with pytest.raises(TypeError, match=r"Escaped uses a custom metaclass"):

        class Escaped(ts.Outcome, metaclass=Skipping):
            DONE = enum.auto()

            def is_done(self) -> bool:
                return True


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
            def __new__(cls, value: int) -> Made:
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

    with pytest.raises(TypeError, match=r"Annotated defines '__annotat(ions__|e_func__)'"):

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


def test_an_outcome_is_not_rejected_by_an_outcome_declared_before_it() -> None:
    class Delivery(ts.Outcome):
        SENT = enum.auto()
        RETURNED = enum.auto()

    class Refund(ts.Outcome):
        ISSUED = enum.auto()
        DECLINED = enum.auto()

    assert list(Delivery) == [Delivery.SENT, Delivery.RETURNED]
    assert list(Refund) == [Refund.ISSUED, Refund.DECLINED]


def test_the_allowlist_does_not_depend_on_the_name_of_the_class_that_produced_it() -> None:
    class Short(ts.Outcome):
        pass

    class AConsiderablyLongerName(ts.Outcome):
        pass

    assert frozenset(Short.__dict__) == outcome._GENERATED
    assert frozenset(AConsiderablyLongerName.__dict__) == outcome._GENERATED


def test_a_name_the_machinery_writes_and_then_removes_never_reaches_the_gate() -> None:
    halves: list[frozenset[str]] = []

    class Watched(enum.Enum):
        def __init_subclass__(cls, **kwargs: object) -> None:
            super().__init_subclass__(**kwargs)
            halves.append(frozenset(cls.__dict__))

    class Ferry(Watched):
        CONTINUE = enum.auto()
        DONE = enum.auto()

    transient = halves[0] - frozenset(Ferry.__dict__)
    assert transient

    class Ferry(ts.Outcome):  # type: ignore[no-redef]
        CONTINUE = enum.auto()
        DONE = enum.auto()

    assert transient.isdisjoint(frozenset(Ferry.__dict__))
    assert list(Ferry) == [Ferry.CONTINUE, Ferry.DONE]


def test_the_gate_reads_an_allowlist_no_class_body_can_widen() -> None:
    assert isinstance(outcome._GENERATED, frozenset)

    with pytest.raises(TypeError, match=r"Widened defines 'is_done'"):

        class Widened(ts.Outcome):
            DONE = enum.auto()

            @property
            def is_done(self) -> bool:
                return True
