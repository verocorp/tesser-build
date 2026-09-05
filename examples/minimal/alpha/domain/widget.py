from __future__ import annotations

import enum
import typing

import tesser.domain as ts

import alpha.domain.clearance as clearance
import kernel.identity as identity
import shared.label as label
import tesser.errors as errors
import tesser.serialization as serialization


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
        self._id = identity.Identity(part_spec.id)

    @property
    def identity(self) -> identity.Identity:
        return self._id


class Taken(ts.Outcome):
    TAKEN = enum.auto()
    HELD = enum.auto()


_KEPT: typing.Final[clearance.Standing] = clearance.Standing("kept")
_RELEASED: typing.Final[clearance.Standing] = clearance.Standing("released")


class WidgetSpec(ts.Spec):

    def __init__(self, name: str, part: PartSpec, standing: str) -> None:
        self.name = name
        self.part = part
        self.standing = standing


class Widget(ts.AggregateRoot):

    def __init__(self, widget_spec: WidgetSpec) -> None:
        self._name = Name(widget_spec.name)
        self._part = Part(widget_spec.part)
        self._label = label.Label(widget_spec.name)
        self._standing = clearance.Standing(widget_spec.standing)

    @property
    def identity(self) -> Name:
        return self._name

    @property
    def part(self) -> Part:
        return self._part

    @property
    def standing(self) -> clearance.Standing:
        return self._standing

    def take(self, part_spec: PartSpec) -> Taken:
        part = Part(part_spec)
        if part == self._part:
            return Taken.HELD
        self._part = part
        return Taken.TAKEN

    def clear(self, clearance_spec: clearance.ClearanceSpec) -> None:
        domain_clearance = clearance.Clearance(clearance_spec)
        match domain_clearance.decide():
            case clearance.Verdict.CLEARED:
                self._standing = _KEPT
            case clearance.Verdict.REFUSED:
                self._standing = _RELEASED
            case _ as never:
                typing.assert_never(never)
