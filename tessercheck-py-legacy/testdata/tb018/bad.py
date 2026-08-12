from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


def canonical_str(value: str) -> str:
    return value


def canonical_decimal(value: Decimal) -> str:
    return str(value)


def canonical_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


@dataclass(frozen=True)
class Slug:
    _value: str

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class Price:
    _value: Decimal

    def __str__(self) -> str:
        return str(self._value)


@dataclass(frozen=True)
class Occurred:
    _value: datetime

    def __str__(self) -> str:
        return self._value.isoformat()


@dataclass(frozen=True)
class Count:
    _value: int

    def __int__(self) -> int:
        return int(self._value)


@dataclass(frozen=True)
class Fee:
    _value: Decimal

    def __str__(self) -> str:
        return canonical_str(str(self._value))


@dataclass(frozen=True)
class Reference:
    _value: str

    def __str__(self) -> str:
        return canonical_str(self._value).upper()
