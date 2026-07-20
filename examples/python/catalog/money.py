from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


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
            raise ValueError(f"invalid amount: {value!r}") from e
        if parsed < 0:
            raise ValueError(f"amount must not be negative: {parsed}")
        object.__setattr__(self, "_value", parsed)

    def add(self, other: "MoneyAmount") -> "MoneyAmount":
        return MoneyAmount(str(self._value + other._value))

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

    def add(self, other: "Money") -> "Money":
        if self._currency != other._currency:
            raise ValueError(f"cannot add {self._currency} and {other._currency}")
        total = self._amount.add(other._amount)
        return Money(MoneySpec(amount=str(total), currency=str(self._currency)))
