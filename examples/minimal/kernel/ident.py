from __future__ import annotations

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization


class Ident(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("empty_ident", "an ident is never empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)
