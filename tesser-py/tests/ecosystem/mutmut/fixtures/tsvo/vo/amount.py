import tesser.domain as ts


class Amount(ts.ValueObject):

    _value: int

    def __init__(self, value: int) -> None:
        if value < 0:
            raise ValueError(f"amount must not be negative: {value}")
        object.__setattr__(self, "_value", value)

    def add(self, other: "Amount") -> "Amount":
        return Amount(self._value + other._value)

    def value(self) -> int:
        return self._value
