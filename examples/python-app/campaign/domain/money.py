from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Final

import tesser.domain as ts

from tesser.errors import invalid
from tesser.serialization import canonical_decimal, canonical_str

_CURRENCY_RE: Final[re.Pattern[str]] = re.compile(r"[A-Z]{3}")


class MoneySpec(ts.Spec):

    def __init__(self, amount: str, currency: str) -> None:
        self.amount = amount
        self.currency = currency


class MoneyAmount(ts.ValueObject):

    def __init__(self, value: str) -> None:
        try:
            parsed = Decimal(value)
        except InvalidOperation as e:
            raise invalid("invalid_budget_amount", f"budget amount {value!r} is not a number") from e
        if parsed < 0:
            raise invalid("invalid_budget_amount", f"budget amount must not be negative: {parsed}")
        object.__setattr__(self, "_value", parsed)

    def __str__(self) -> str:
        return canonical_decimal(self._value)

    _value: Decimal


class MoneyCurrency(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CURRENCY_RE.fullmatch(value):
            raise invalid("invalid_budget_currency", f"budget currency {value!r} must be 3 uppercase letters")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Money(ts.ValueObject):

    def __init__(self, amount: str, currency: str) -> None:
        object.__setattr__(self, "_amount", MoneyAmount(amount))
        object.__setattr__(self, "_currency", MoneyCurrency(currency))

    @property
    def amount(self) -> MoneyAmount:
        return self._amount

    @property
    def currency(self) -> MoneyCurrency:
        return self._currency

    _amount: MoneyAmount
    _currency: MoneyCurrency
