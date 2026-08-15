from dataclasses import dataclass


@dataclass(frozen=True)
class Amount:

    _value: int

    def __post_init__(self) -> None:
        if self._value < 0:
            raise ValueError(f"amount must not be negative: {self._value}")

    def add(self, other: "Amount") -> "Amount":
        return Amount(self._value + other._value)

    def value(self) -> int:
        return self._value
