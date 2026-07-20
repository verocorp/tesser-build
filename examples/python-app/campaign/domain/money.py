from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from errors import invalid
from serialization import canonical_decimal, canonical_str

_CURRENCY_RE = re.compile(r"[A-Z]{3}")


@dataclass(frozen=True)
class MoneySpec:
    amount: str
    currency: str


@dataclass(frozen=True, init=False)
class MoneyAmount:
    _value: Decimal

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


@dataclass(frozen=True)
class MoneyCurrency:
    _value: str

    def __post_init__(self) -> None:
        if not _CURRENCY_RE.fullmatch(self._value):
            raise invalid("invalid_budget_currency", f"budget currency {self._value!r} must be 3 uppercase letters")

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True, init=False)
class Money:
    _amount: MoneyAmount
    _currency: MoneyCurrency

    def __init__(self, spec: MoneySpec) -> None:
        object.__setattr__(self, "_amount", MoneyAmount(spec.amount))
        object.__setattr__(self, "_currency", MoneyCurrency(spec.currency))

    @property
    def amount(self) -> MoneyAmount:
        return self._amount

    @property
    def currency(self) -> MoneyCurrency:
        return self._currency
