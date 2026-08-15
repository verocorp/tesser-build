from __future__ import annotations

import re
from typing import Final

import tesser.domain as ts

from kernel.slug import Slug as Slug
from tesser.errors import invalid
from tesser.serialization import canonical_str

_URL_RE: Final[re.Pattern[str]] = re.compile(r"https?://\S+")


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _URL_RE.fullmatch(value):
            raise invalid("invalid_target_url", f"target url {value!r} must be http(s)")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Decision(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if value not in ("allowed", "denied"):
            raise invalid("invalid_decision", f"decision {value!r} must be allowed or denied")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Reason(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise invalid("invalid_reason", "reason must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str
