from __future__ import annotations

import tesser.domain as ts

import tesser.serialization as serialization


class Persona(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value.strip():
            raise ValueError("a persona says who the agent is on the call")
        object.__setattr__(self, "_value", value.strip())

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)
