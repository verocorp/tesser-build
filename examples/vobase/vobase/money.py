from decimal import Decimal, InvalidOperation

import tesser.domain as ts

from vobase.serialization import canonical_decimal, canonical_str


class MoneySpec(ts.ValueObject):

    amount: str
    currency: str

    def __init__(self, amount: str, currency: str) -> None:
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "currency", currency)


class MoneyAmount(ts.ValueObject):

    _value: Decimal

    def __init__(self, value: str) -> None:
        try:
            parsed = Decimal(value)
        except InvalidOperation as e:
            raise ValueError(f"invalid amount: {value!r}") from e
        if not parsed.is_finite():
            raise ValueError(f"amount must be finite: {value!r}")
        if parsed < 0:
            raise ValueError(f"amount must not be negative: {parsed}")
        object.__setattr__(self, "_value", parsed)

    def add(self, other: "MoneyAmount") -> "MoneyAmount":
        return MoneyAmount(canonical_decimal(self._value + other._value))

    def __str__(self) -> str:
        return canonical_decimal(self._value)


class MoneyCurrency(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value.strip():
            raise ValueError("currency is required")
        object.__setattr__(self, "_value", value)

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
