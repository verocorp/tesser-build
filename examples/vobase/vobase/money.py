import re
from decimal import Decimal, Rounded, localcontext

import tesser.domain as ts

from vobase.serialization import (
    CANONICAL_DECIMAL_MAX_ADJUSTED,
    canonical_decimal,
    canonical_str,
)

_AMOUNT_PATTERN = re.compile(r"-?[0-9]+(\.[0-9]+)?")
_CURRENCY_PATTERN = re.compile(r"[A-Z]{3}")
_AMOUNT_PRECISION = 28


class MoneySpec(ts.ValueObject):

    amount: str
    currency: str

    def __init__(self, amount: str, currency: str) -> None:
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "currency", currency)


class MoneyAmount(ts.ValueObject):

    _value: Decimal

    def __init__(self, value: str) -> None:
        if _AMOUNT_PATTERN.fullmatch(value) is None:
            raise ValueError(f"invalid amount: {value!r}")
        parsed = Decimal(value)
        if parsed < 0:
            raise ValueError(f"amount must not be negative: {parsed}")
        if parsed == 0:
            parsed = Decimal(0)
        if abs(parsed.adjusted()) > CANONICAL_DECIMAL_MAX_ADJUSTED:
            raise ValueError(f"amount out of range: {value!r}")
        object.__setattr__(self, "_value", parsed)

    def add(self, other: "MoneyAmount") -> "MoneyAmount":
        with localcontext() as ctx:
            ctx.prec = _AMOUNT_PRECISION
            ctx.traps[Rounded] = True
            try:
                total = self._value + other._value
            except ArithmeticError as e:
                raise ValueError("amount arithmetic exceeds supported precision") from e
        return MoneyAmount(canonical_decimal(total))

    def __str__(self) -> str:
        return canonical_decimal(self._value)


class MoneyCurrency(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        stripped = value.strip()
        if not stripped:
            raise ValueError("currency is required")
        if _CURRENCY_PATTERN.fullmatch(stripped) is None:
            raise ValueError(f"currency must be 3 uppercase letters: {value!r}")
        object.__setattr__(self, "_value", stripped)

    def __str__(self) -> str:
        return canonical_str(self._value)


class Money(ts.ValueObject):

    _amount: MoneyAmount
    _currency: MoneyCurrency

    def __init__(self, spec: MoneySpec) -> None:
        object.__setattr__(self, "_amount", MoneyAmount(spec.amount))
        object.__setattr__(self, "_currency", MoneyCurrency(spec.currency))

    def amount(self) -> MoneyAmount:
        return self._amount

    def currency(self) -> MoneyCurrency:
        return self._currency

    def add(self, other: "Money") -> "Money":
        if self._currency != other._currency:
            raise ValueError(f"cannot add {self._currency} and {other._currency}")
        total = self._amount.add(other._amount)
        return Money(MoneySpec(amount=str(total), currency=str(self._currency)))
