from __future__ import annotations

import tesser.domain as ts

import tesser.serialization as serialization


class Label(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)
