from __future__ import annotations

import re
import typing

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_SLUG_RE: typing.Final[re.Pattern[str]] = re.compile(r"[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?")


class Slug(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _SLUG_RE.fullmatch(value):
            raise errors.invalid("invalid_slug", f"slug {value!r} must be 1-64 lowercase alnum/hyphen")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str
