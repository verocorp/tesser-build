from dataclasses import dataclass
from typing import Protocol


class Sink(Protocol):
    def put(self, value: str) -> None: ...


@dataclass(frozen=True)
class SlugSpec:
    value: str


@dataclass(frozen=True)
class Slug:
    _value: str

    def __str__(self) -> str:
        return self._value

    def to_spec(self) -> SlugSpec:
        return SlugSpec(value=self._value)


@dataclass(frozen=True)
class Code:
    _value: str

    def __str__(self) -> str:
        return self._value

    def emit(self, sink: Sink) -> None:
        sink.put(self._value)


@dataclass(frozen=True)
class Count:
    _value: int

    def __int__(self) -> int:
        return self._value

    def __str__(self) -> str:
        return str(self._value)


@dataclass(frozen=True)
class Weight:
    _value: str

    def __int__(self) -> int:
        return int(self._value)


@dataclass(frozen=True)
class Amount:
    _value: str

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class Currency:
    _value: str

    def __str__(self) -> str:
        return self._value


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

    def __str__(self) -> str:
        return f"{self._amount} {self._currency}"


@dataclass(frozen=True)
class Label:
    _value: str

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class Labels:
    _values: tuple[Label, ...]

    def __str__(self) -> str:
        return ",".join(str(v) for v in self._values)
