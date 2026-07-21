from dataclasses import dataclass
from decimal import Decimal


def canonical_decimal(value: Decimal) -> str:
    return str(value)


def canonical_int(value: int) -> int:
    return value


def canonical_str(value: str) -> str:
    return value


@dataclass(frozen=True)
class Slug:
    _value: str

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class Count:
    _value: int

    def __int__(self) -> int:
        return canonical_int(self._value)


@dataclass(frozen=True)
class MoneyAmount:
    _value: Decimal

    def __str__(self) -> str:
        return canonical_decimal(self._value)


@dataclass(frozen=True)
class MoneyCurrency:
    _value: str

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class MoneySpec:
    amount: str
    currency: str


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


@dataclass(frozen=True)
class Label:
    _value: str

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class Labels:
    _values: tuple[Label, ...]

    def all(self) -> tuple[Label, ...]:
        return self._values
