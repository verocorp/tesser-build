from __future__ import annotations

import re
import typing

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_URL_RE: typing.Final[re.Pattern[str]] = re.compile(r"https?://\S+")


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _URL_RE.fullmatch(value):
            raise errors.invalid("invalid_target_url", f"target url {value!r} must be http(s)")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class Decision(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if value not in ("allowed", "denied"):
            raise errors.invalid("invalid_decision", f"decision {value!r} must be allowed or denied")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class Reason(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("invalid_reason", "reason must not be empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str
