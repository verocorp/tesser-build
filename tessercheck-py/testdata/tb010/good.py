from dataclasses import dataclass


def canonical_str(value: str) -> str:
    return value


@dataclass(frozen=True)
class Slug:
    _value: str

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class SlugSpec:
    value: str


@dataclass(frozen=True)
class Amount:
    _value: str

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class Price:
    _amount: Amount

    @property
    def amount(self) -> Amount:
        return self._amount
