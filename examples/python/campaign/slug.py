import re
from dataclasses import dataclass

# _SLUG_PATTERN enforces the business rule: 4-20 characters, lowercase
# letters, digits, and hyphens only.
_SLUG_PATTERN = re.compile(r"^[a-z0-9-]{4,20}$")


@dataclass(frozen=True)
class Slug:
    """The short code of a ShortLink (e.g. "spring-sale"). Simple, single-value
    value object: one field, native (field-wise) equality — a slug has exactly
    one representation.
    """

    _value: str

    def __post_init__(self) -> None:
        if not _SLUG_PATTERN.match(self._value):
            raise ValueError(
                f"invalid slug {self._value!r}: must be 4-20 characters of "
                "lowercase letters, digits, and hyphens"
            )

    def __str__(self) -> str:
        return self._value
