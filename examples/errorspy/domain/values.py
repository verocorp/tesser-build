from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from errors import invalid

_SLUG_PATTERN = re.compile(r"^[a-z0-9-]{4,20}$")


@dataclass(frozen=True)
class Slug:

    _value: str

    def __post_init__(self) -> None:
        if not _SLUG_PATTERN.match(self._value):
            raise invalid(
                "bad_slug",
                f"invalid slug {self._value!r}: must be 4-20 chars of lowercase "
                "letters, digits, and hyphens",
                field="slug",
            )

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class TargetURL:

    _value: str

    def __post_init__(self) -> None:
        if not (self._value.startswith("http://") or self._value.startswith("https://")):
            raise invalid(
                "bad_target_url",
                f"invalid target url {self._value!r}: must start with http:// or https://",
                field="target_url",
            )

    def __str__(self) -> str:
        return self._value


@dataclass(frozen=True)
class DateWindowSpec:

    start: str
    end: str


@dataclass(frozen=True, init=False)
class DateWindow:

    _start: date
    _end: date

    def __init__(self, spec: DateWindowSpec) -> None:
        start = _parse_date(spec.start, field="start")
        end = _parse_date(spec.end, field="end")
        if start >= end:
            raise invalid(
                "window_order",
                f"window start {start.isoformat()} must be before "
                f"end {end.isoformat()}",
                field="start",
            )
        object.__setattr__(self, "_start", start)
        object.__setattr__(self, "_end", end)

    @property
    def start(self) -> date:
        return self._start

    @property
    def end(self) -> date:
        return self._end


def _parse_date(value: str, *, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise invalid("bad_date", f"invalid {field} date {value!r}", field=field) from e
