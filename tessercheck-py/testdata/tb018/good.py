from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal


def canonical_str(value: str) -> str:
    return value


def canonical_int(value: int) -> int:
    return value


def canonical_float(value: float) -> float:
    return value


def canonical_bytes(value: bytes) -> bytes:
    return value


def canonical_decimal(value: Decimal) -> str:
    return str(value)


def canonical_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


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
class Ratio:
    _value: float

    def __float__(self) -> float:
        return canonical_float(self._value)


@dataclass(frozen=True)
class Digest:
    _value: bytes

    def __bytes__(self) -> bytes:
        return canonical_bytes(self._value)


@dataclass(frozen=True)
class Price:
    _value: Decimal

    def __str__(self) -> str:
        return canonical_decimal(self._value)


@dataclass(frozen=True)
class Occurred:
    _value: datetime

    def __str__(self) -> str:
        return canonical_datetime(self._value)


@dataclass(frozen=True)
class Day:
    _value: date

    def __str__(self) -> str:
        return self._value.isoformat()


@dataclass(frozen=True)
class Amount:
    _value: str

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class Currency:
    _value: str

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class MoneySpec:
    amount: str
    currency: str


@dataclass(frozen=True, init=False)
class Money:
    _amount: Amount
    _currency: Currency

    def __init__(self, spec: MoneySpec) -> None:
        object.__setattr__(self, "_amount", Amount(spec.amount))
        object.__setattr__(self, "_currency", Currency(spec.currency))

    @property
    def amount(self) -> Amount:
        return self._amount

    @property
    def currency(self) -> Currency:
        return self._currency
