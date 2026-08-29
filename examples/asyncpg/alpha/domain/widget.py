from __future__ import annotations

import enum

import tesser.domain as ts

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

    def __init__(self, spec: PartSpec) -> None:
        self._id = identity.Identity(spec.id)

    @property
    def identity(self) -> identity.Identity:
        return self._id


class Taken(ts.Outcome):
    TAKEN = enum.auto()
    HELD = enum.auto()


class WidgetSpec(ts.Spec):

    def __init__(self, name: str, part: PartSpec) -> None:
        self.name = name
        self.part = part


class Widget(ts.AggregateRoot):

    def __init__(self, spec: WidgetSpec) -> None:
        self._name = Name(spec.name)
        self._part = Part(spec.part)
        self._label = label.Label(spec.name)

    @property
    def identity(self) -> Name:
        return self._name

    @property
    def part(self) -> Part:
        return self._part

    def take(self, spec: PartSpec) -> Taken:
        part = Part(spec)
        if part == self._part:
            return Taken.HELD
        self._part = part
        return Taken.TAKEN
