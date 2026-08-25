from __future__ import annotations

import re
import decimal
import typing

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_CURRENCY_RE: typing.Final[re.Pattern[str]] = re.compile(r"[A-Z]{3}")


class MoneySpec(ts.Spec):

    def __init__(self, amount: str, currency: str) -> None:
        self.amount = amount
        self.currency = currency


class MoneyAmount(ts.ValueObject):

    def __init__(self, value: str) -> None:
        try:
            parsed = decimal.Decimal(value)
        except decimal.InvalidOperation as e:
            raise errors.invalid("invalid_budget_amount", f"budget amount {value!r} is not a number") from e
        if not parsed.is_finite():
            raise errors.invalid("invalid_budget_amount", f"budget amount {value!r} is not a finite number")
        if parsed < 0:
            raise errors.invalid("invalid_budget_amount", f"budget amount must not be negative: {parsed}")
        object.__setattr__(self, "_value", parsed)

    def __str__(self) -> str:
        return serialization.canonical_decimal(self._value)

    _value: decimal.Decimal


class MoneyCurrency(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CURRENCY_RE.fullmatch(value):
            raise errors.invalid("invalid_budget_currency", f"budget currency {value!r} must be 3 uppercase letters")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class Money(ts.ValueObject):

    def __init__(self, spec: MoneySpec) -> None:
        object.__setattr__(self, "_amount", MoneyAmount(spec.amount))
        object.__setattr__(self, "_currency", MoneyCurrency(spec.currency))

    @property
    def amount(self) -> MoneyAmount:
        return self._amount

    @property
    def currency(self) -> MoneyCurrency:
        return self._currency

    _amount: MoneyAmount
    _currency: MoneyCurrency
