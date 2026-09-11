from __future__ import annotations

import typing

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_MAX_UNITS: typing.Final[int] = 1_000_000
_MAX_CENTS: typing.Final[int] = 10**12


class Quantity(ts.ValueObject):

    _value: int

    def __init__(self, value: int) -> None:
        if value < 1:
            raise errors.invalid("quantity_below_one", "an order is for at least one unit")
        if value > _MAX_UNITS:
            raise errors.invalid("quantity_above_maximum", f"an order is for at most {_MAX_UNITS} units")
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return serialization.canonical_int(self._value)


class PriceSpec(ts.Spec):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class Price(ts.ValueObject):

    _cents: int

    def __init__(self, spec: PriceSpec) -> None:
        if spec.cents < 0:
            raise errors.invalid("negative_price", "a price is never negative")
        if spec.cents > _MAX_CENTS:
            raise errors.invalid("price_above_maximum", f"a price, or a total, is at most {_MAX_CENTS} cents")
        object.__setattr__(self, "_cents", spec.cents)

    def __int__(self) -> int:
        return serialization.canonical_int(self._cents)

    def times(self, quantity: Quantity) -> Price:
        return Price(PriceSpec(cents=self._cents * int(quantity)))
