from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from errors import DomainError, invalid, wrap

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
class Day:

    _value: date

    def __init__(self, value: str) -> None:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as e:
            raise invalid("bad_date", f"invalid date {value!r}") from e
        object.__setattr__(self, "_value", parsed)

    def __str__(self) -> str:
        return self._value.isoformat()

    def before(self, other: "Day") -> bool:
        return self._value < other._value


@dataclass(frozen=True, init=False)
class DateWindow:

    _start: Day
    _end: Day

    def __init__(self, spec: DateWindowSpec) -> None:
        start = _day(spec.start, field="start")
        end = _day(spec.end, field="end")
        if not start.before(end):
            raise invalid(
                "window_order",
                f"window start {start} must be before end {end}",
                field="start",
            )
        object.__setattr__(self, "_start", start)
        object.__setattr__(self, "_end", end)

    @property
    def start(self) -> Day:
        return self._start

    @property
    def end(self) -> Day:
        return self._end


def _day(value: str, *, field: str) -> Day:
    try:
        return Day(value)
    except DomainError as e:
        raise wrap(e, f"invalid {field} date {value!r}", field=field) from e.__cause__
