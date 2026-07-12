"""Money — a compound value object. Exact decimal amount, no float drift."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class MoneySpec:
    """Spec: primitive leaves only."""

    amount: str
    currency: str


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    @classmethod
    def from_spec(cls, spec: MoneySpec) -> "Money":
        try:
            amount = Decimal(spec.amount)  # conversion only — no rules here
        except InvalidOperation as e:
            raise ValueError(f"invalid money amount: {spec.amount!r}") from e
        return cls(amount=amount, currency=spec.currency)

    def __post_init__(self) -> None:  # the rules live here, always run
        if not self.currency:
            raise ValueError("currency is required")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError(f"invalid currency code: {self.currency!r}")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(
                f"cannot add {other.currency} to a {self.currency} amount"
            )
        return Money(self.amount + other.amount, self.currency)

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"
