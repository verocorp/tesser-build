from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class MoneySpec:
    """Primitive leaves: amount is a decimal string (e.g. "19.99"), parsed and
    validated by the constructor."""

    amount: str
    currency: str


@dataclass(frozen=True)
class Money:
    """A compound value object: an amount plus a currency. The amount is a
    ``decimal.Decimal`` so values are exact (no float drift).

    Unlike Go's ``*big.Rat`` — where the field is a pointer and ``==`` would
    compare identity — ``Decimal`` has correct *value* equality and hashing
    (``Decimal("1.5") == Decimal("1.50")`` and their hashes match), so the
    frozen dataclass's **default** field-wise ``__eq__``/``__hash__`` is already
    correct across representations. No custom equality is needed here; the
    equality test locks that in (verifying both ``==`` and ``hash``).
    """

    _amount: Decimal
    _currency: str

    @classmethod
    def from_spec(cls, spec: MoneySpec) -> "Money":
        try:
            amount = Decimal(spec.amount)  # conversion only — no rules here
        except InvalidOperation as e:
            raise ValueError(f"invalid amount: {spec.amount!r}") from e
        return cls(_amount=amount, _currency=spec.currency)

    def __post_init__(self) -> None:
        # The rules live here, so they run on every construction path.
        if not self._currency:
            raise ValueError("currency is required")
        if self._amount < 0:
            raise ValueError(f"amount must not be negative: {self._amount}")

    def add(self, other: "Money") -> "Money":
        """Domain behavior: same-currency sum, returning a new value."""
        if self._currency != other._currency:
            raise ValueError(f"cannot add {self._currency} and {other._currency}")
        return Money(self._amount + other._amount, self._currency)

    def __str__(self) -> str:
        # Display only — never an equality path. The Decimal amount leaves the
        # domain only here (formatted) — never via a raw accessor.
        return f"{self._amount:.2f} {self._currency}"
