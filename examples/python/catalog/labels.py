from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, init=False)
class Labels:

    _values: tuple[tuple[str, str], ...]

    def __init__(self, values: Mapping[str, str]) -> None:
        object.__setattr__(self, "_values", tuple(sorted(values.items())))

    def get(self, key: str) -> str | None:
        return dict(self._values).get(key)

    def as_dict(self) -> dict[str, str]:
        return dict(self._values)

    def __len__(self) -> int:
        return len(self._values)
