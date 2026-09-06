from __future__ import annotations

import enum
import typing

import tesser.domain as ts

import alpha.domain.kernel as kernel
import tesser.errors as errors
import tesser.serialization as serialization


class Verdict(ts.Outcome):
    CLEARED = enum.auto()
    REFUSED = enum.auto()


class ClearanceSpec(ts.Spec):

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict


class Clearance(ts.ValueObject):

    _verdict: str

    def __init__(self, clearance_spec: ClearanceSpec) -> None:
        if clearance_spec.verdict not in ("ok", "refused"):
            raise errors.invalid("invalid_verdict", f"verdict {clearance_spec.verdict!r} is not a verdict")
        object.__setattr__(self, "_verdict", clearance_spec.verdict)

    def decide(self) -> Verdict:
        if self._verdict == "ok":
            return Verdict.CLEARED
        return Verdict.REFUSED

    def __str__(self) -> str:
        return serialization.canonical_str(self._verdict)


class Standing(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("kept", "released"):
            raise errors.invalid("invalid_standing", f"standing {value!r} is not a standing")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Name(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("empty_name", "a name is never empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class PartSpec(ts.Spec):

    def __init__(self, id: str) -> None:
        self.id = id


class Part(ts.Entity):

    def __init__(self, part_spec: PartSpec) -> None:
        self._id = kernel.Identity(part_spec.id)

    @property
    def identity(self) -> kernel.Identity:
        return self._id


class Taken(ts.Outcome):
    TAKEN = enum.auto()
    HELD = enum.auto()


_KEPT: typing.Final[Standing] = Standing("kept")
_RELEASED: typing.Final[Standing] = Standing("released")


class WidgetSpec(ts.Spec):

    def __init__(self, name: str, part: PartSpec, standing: str) -> None:
        self.name = name
        self.part = part
        self.standing = standing


class Widget(ts.AggregateRoot):

    def __init__(self, widget_spec: WidgetSpec) -> None:
        self._name = Name(widget_spec.name)
        self._part = Part(widget_spec.part)
        self._label = kernel.Label(widget_spec.name)
        self._standing = Standing(widget_spec.standing)

    @property
    def identity(self) -> Name:
        return self._name

    @property
    def part(self) -> Part:
        return self._part

    @property
    def standing(self) -> Standing:
        return self._standing

    def take(self, part_spec: PartSpec) -> Taken:
        part = Part(part_spec)
        if part == self._part:
            return Taken.HELD
        self._part = part
        return Taken.TAKEN

    def clear(self, clearance_spec: ClearanceSpec) -> None:
        clearance = Clearance(clearance_spec)
        match clearance.decide():
            case Verdict.CLEARED:
                self._standing = _KEPT
            case Verdict.REFUSED:
                self._standing = _RELEASED
            case _ as never:
                typing.assert_never(never)
