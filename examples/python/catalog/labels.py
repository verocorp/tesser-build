from collections.abc import Mapping
from dataclasses import dataclass, field


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

    def as_dict(self) -> dict[str, str]:
        return dict(self._values)

    def __len__(self) -> int:
        return len(self._values)
