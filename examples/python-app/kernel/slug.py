from __future__ import annotations

import re
from typing import Final

import tesser.domain as ts

from errors import invalid  # tessercheck:ignore TB062
from serialization import canonical_str  # tessercheck:ignore TB062

_SLUG_RE: Final[re.Pattern[str]] = re.compile(r"[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?")


class Slug(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _SLUG_RE.fullmatch(value):
            raise invalid("invalid_slug", f"slug {value!r} must be 1-64 lowercase alnum/hyphen")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str
