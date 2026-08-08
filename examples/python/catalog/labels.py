from collections.abc import Mapping
from dataclasses import dataclass

from serialization import canonical_str


@dataclass(frozen=True)
class LabelValue:

    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("label value must not be empty")

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True, init=False)
class Labels:

    _values: tuple[tuple[str, str], ...]

    def __init__(self, values: Mapping[str, str]) -> None:
        object.__setattr__(self, "_values", tuple(sorted(values.items())))

    def get(self, key: str) -> LabelValue | None:
        raw = dict(self._values).get(key)
        return LabelValue(raw) if raw is not None else None

    def __len__(self) -> int:
        return len(self._values)
