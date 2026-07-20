from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class MoneySpec:

    amount: str
    currency: str


@dataclass(frozen=True)
class MoneyAmount:

    _value: Decimal

    @classmethod
    def parse(cls, raw: str) -> "MoneyAmount":
        try:
            value = Decimal(raw)
        except InvalidOperation as e:
            raise ValueError(f"invalid amount: {raw!r}") from e
        return cls(value)

    def __post_init__(self) -> None:
        if self._value < 0:
            raise ValueError(f"amount must not be negative: {self._value}")

    def add(self, other: "MoneyAmount") -> "MoneyAmount":
        return MoneyAmount(self._value + other._value)

    def __str__(self) -> str:
        return str(self._value)


@dataclass(frozen=True)
class MoneyCurrency:

    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("currency is required")

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class Money:

    _amount: MoneyAmount
    _currency: MoneyCurrency

    @classmethod
    def from_spec(cls, spec: MoneySpec) -> "Money":
        return cls(MoneyAmount.parse(spec.amount), MoneyCurrency(spec.currency))

    @property
    def amount(self) -> MoneyAmount:
        return self._amount

    @property
    def currency(self) -> MoneyCurrency:
        return self._currency

    def add(self, other: "Money") -> "Money":
        if self._currency != other._currency:
            raise ValueError(f"cannot add {self._currency} and {other._currency}")
        return Money(self._amount.add(other._amount), self._currency)

    def __str__(self) -> str:
        return f"{self._amount} {self._currency}"
