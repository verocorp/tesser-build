from __future__ import annotations

import re
from datetime import date
from typing import Final

import tesser.domain as ts

from tesser.errors import DomainError, invalid, wrap
from tesser.serialization import canonical_str

_SLUG_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9-]{4,20}$")
_LINK_STATES: Final[frozenset[str]] = frozenset({"active", "inactive"})


class Slug(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _SLUG_PATTERN.match(value):
            raise invalid(
                "bad_slug",
                f"invalid slug {value!r}: must be 4-20 chars of lowercase "
                "letters, digits, and hyphens",
                field="slug",
            )
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not (value.startswith("http://") or value.startswith("https://")):
            raise invalid(
                "bad_target_url",
                f"invalid target url {value!r}: must start with http:// or https://",
                field="target_url",
            )
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class LinkStatus(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if value not in _LINK_STATES:
            raise invalid(
                "bad_link_status",
                f"invalid link status {value!r}: must be one of "
                f"{', '.join(sorted(_LINK_STATES))}",
                field="status",
            )
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class Day(ts.ValueObject):

    def __init__(self, value: str) -> None:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as e:
            raise invalid("bad_date", f"invalid date {value!r}") from e
        object.__setattr__(self, "_value", parsed)

    def __str__(self) -> str:
        return self._value.isoformat()

    def _before(self, other: "Day") -> bool:
        return self._value < other._value

    _value: date


class DateWindowSpec(ts.Spec):

    def __init__(self, start: str, end: str) -> None:
        self.start = start
        self.end = end


class DateWindow(ts.ValueObject):

    def __init__(self, start_value: str, end_value: str) -> None:
        start = _day(start_value, field="start")
        end = _day(end_value, field="end")
        if not start._before(end):
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

    _start: Day
    _end: Day


@ts.do_not_use_function
def _day(value: str, *, field: str) -> Day:
    try:
        return Day(value)
    except DomainError as e:
        raise wrap(e, f"invalid {field} date {value!r}", field=field) from e.__cause__
