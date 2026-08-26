from __future__ import annotations

import ast
import builtins
import collections.abc as abc
import copy
import datetime
import decimal
import enum
import fractions
import io
import math
import re
import statistics
import tokenize
import typing
import urllib.parse

import tesser.domain as ts

import alpha.domain.state as state
import kernel.ident as ident
import shared.label as label
import tesser.errors as errors
import tesser.serialization as serialization

_NAME: typing.Final[re.Pattern[str]] = re.compile(r"[a-z]+")


class Name(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not _NAME.fullmatch(value):
            raise errors.invalid("bad_name", "a name is lowercase letters")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Count(ts.ValueObject):

    _value: int

    def __init__(self, value: int) -> None:
        if value < 0:
            raise errors.invalid("bad_count", "a count is never negative")
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return serialization.canonical_int(self._value)


class PairSpec(ts.Spec):

    def __init__(self, name: str, count: int) -> None:
        self.name = name
        self.count = count


class Pair(ts.ValueObject):

    _name: Name
    _count: Count

    def __init__(self, spec: PairSpec) -> None:
        object.__setattr__(self, "_name", Name(spec.name))
        object.__setattr__(self, "_count", Count(spec.count))

    @property
    def name(self) -> Name:
        return self._name

    @property
    def count(self) -> Count:
        return self._count


class PartSpec(ts.Spec):

    def __init__(self, id: str, state: state.State) -> None:
        self.id = id
        self.state = state


class Part(ts.Entity):

    def __init__(self, spec: PartSpec) -> None:
        self._id = ident.Ident(spec.id)
        self._state = spec.state

    @property
    def identity(self) -> ident.Ident:
        return self._id

    @property
    def state(self) -> state.State:
        return self._state

    def toggle(self) -> None:
        self._state = state.State.OFF if self._state is state.State.ON else state.State.ON


class WholeSpec(ts.Spec):

    def __init__(self, id: str, pair: PairSpec, parts: tuple[PartSpec, ...], other: str) -> None:
        self.id = id
        self.pair = pair
        self.parts = parts
        self.other = other


class Whole(ts.AggregateRoot):

    def __init__(self, spec: WholeSpec) -> None:
        self._id = ident.Ident(spec.id)
        self._pair = Pair(spec.pair)
        self._parts = tuple(Part(part) for part in spec.parts)
        self._other = ident.Ident(spec.other)
        self._label = label.Label(spec.id)

    @property
    def identity(self) -> ident.Ident:
        return self._id

    @property
    def pair(self) -> Pair:
        return self._pair

    @property
    def parts(self) -> tuple[Part, ...]:
        return tuple(self._parts)

    @property
    def other(self) -> ident.Ident:
        return self._other

    @property
    def label(self) -> label.Label:
        return self._label

    def toggle_all(self) -> None:
        for part in self._parts:
            part.toggle()
