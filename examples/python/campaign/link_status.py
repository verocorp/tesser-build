from dataclasses import dataclass
from typing import Final

from serialization import canonical_str

_STATES: Final[frozenset[str]] = frozenset({"active", "inactive"})


@dataclass(frozen=True)
class LinkStatus:

    _value: str

    def __post_init__(self) -> None:
        if self._value not in _STATES:
            raise ValueError(
                f"invalid link status {self._value!r}: must be one of "
                f"{', '.join(sorted(_STATES))}"
            )

    def __str__(self) -> str:
        return canonical_str(self._value)
