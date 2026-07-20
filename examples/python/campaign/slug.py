import re
from dataclasses import dataclass

from serialization import canonical_str

_SLUG_PATTERN = re.compile(r"^[a-z0-9-]{4,20}$")


@dataclass(frozen=True)
class Slug:

    _value: str

    def __post_init__(self) -> None:
        if not _SLUG_PATTERN.match(self._value):
            raise ValueError(
                f"invalid slug {self._value!r}: must be 4-20 characters of "
                "lowercase letters, digits, and hyphens"
            )

    def __str__(self) -> str:
        return canonical_str(self._value)
