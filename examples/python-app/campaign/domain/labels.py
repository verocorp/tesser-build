from __future__ import annotations

import tesser.domain as ts

from errors import invalid  # tessercheck:ignore TB062
from serialization import canonical_str  # tessercheck:ignore TB062


class LabelValue(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise invalid("invalid_label", "label value must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Labels(ts.ValueObject):

    def __init__(self, values: tuple[tuple[str, str], ...]) -> None:
        for key, _ in values:
            if not key:
                raise invalid("invalid_label", "label key must not be empty")
        object.__setattr__(self, "_values", tuple(sorted(values)))

    def get(self, key: str) -> LabelValue | None:
        raw = dict(self._values).get(key)
        return LabelValue(raw) if raw is not None else None

    def __len__(self) -> int:
        return len(self._values)

    _values: tuple[tuple[str, str], ...]
