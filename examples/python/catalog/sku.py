import re
from dataclasses import dataclass

_SKU_PATTERN = re.compile(r"^[A-Z0-9-]{3,20}$")


@dataclass(frozen=True)
class SKU:
    """A product's stock-keeping unit and its identity. Simple, single-value
    value object: one field, native (field-wise) equality."""

    _value: str

    def __post_init__(self) -> None:
        if not _SKU_PATTERN.match(self._value):
            raise ValueError(
                f"invalid SKU {self._value!r}: must be 3-20 characters of "
                "uppercase letters, digits, and hyphens"
            )

    def __str__(self) -> str:
        return self._value
