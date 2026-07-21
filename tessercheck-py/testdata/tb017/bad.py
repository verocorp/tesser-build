from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Slug:
    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("slug must not be empty")

    @classmethod
    def parse(cls, raw: str) -> "Slug":
        return cls(raw.strip().lower())


@dataclass(frozen=True)
class Amount:
    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("amount must not be empty")


@dataclass(frozen=True)
class Currency:
    _value: str

    def __post_init__(self) -> None:
        if len(self._value) != 3:
            raise ValueError("currency must be a 3-letter code")


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

    @staticmethod
    def of(amount: str, currency: str) -> "Money":
        return Money(MoneySpec(amount=amount, currency=currency))

    @property
    def amount(self) -> Amount:
        return self._amount

    @property
    def currency(self) -> Currency:
        return self._currency


@dataclass(frozen=True)
class Labels:
    _values: tuple[tuple[str, str], ...] = field(default=())

    def __post_init__(self) -> None:
        object.__setattr__(self, "_values", tuple(sorted(dict(self._values).items())))

    @classmethod
    def new(cls, values: Mapping[str, str] | None = None) -> "Labels":
        return cls(tuple((values or {}).items()))

    @classmethod
    def require(cls, values: Mapping[str, str] | None = None) -> "Labels":
        if not values:
            raise ValueError("labels must not be empty")
        return cls.new(values)

    def get(self, key: str) -> str | None:
        return dict(self._values).get(key)

    def __len__(self) -> int:
        return len(self._values)
