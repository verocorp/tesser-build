from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class MoneySpec:

    amount: str
    currency: str


@dataclass(frozen=True)
class Money:

    _amount: Decimal
    _currency: str

    @classmethod
    def from_spec(cls, spec: MoneySpec) -> "Money":
        try:
            amount = Decimal(spec.amount)
        except InvalidOperation as e:
            raise ValueError(f"invalid amount: {spec.amount!r}") from e
        return cls(_amount=amount, _currency=spec.currency)

    def __post_init__(self) -> None:
        if not self._currency:
            raise ValueError("currency is required")
        if self._amount < 0:
            raise ValueError(f"amount must not be negative: {self._amount}")

    def add(self, other: "Money") -> "Money":
        if self._currency != other._currency:
            raise ValueError(f"cannot add {self._currency} and {other._currency}")
        return Money(self._amount + other._amount, self._currency)

    def __str__(self) -> str:
        return f"{self._amount:.2f} {self._currency}"
