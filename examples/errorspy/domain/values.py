"""Value objects for the error-norms example.

Every constructor validates and raises a DomainError of kind=validation via the
named ``invalid`` helper, carrying a stable ``code`` and the offending ``field``.
Leaf VOs (Slug, TargetURL) validate a single primitive; the compound VO
(DateWindow) parses two primitives from a spec and wraps each parse failure with
field context (cell C2). Primitives stay hidden behind ``_``-prefixed fields and
leave only through ``__str__`` / accessors — never as raw multi-rep values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from errors import invalid

_SLUG_PATTERN = re.compile(r"^[a-z0-9-]{4,20}$")


@dataclass(frozen=True)
class Slug:
    """C1 leaf VO: the short code of a link (e.g. "spring-sale")."""

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
    """C1 leaf VO: where a short link points."""

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
    """Primitive leaves: ISO-8601 date strings, parsed by the constructor."""

    start: str
    end: str


@dataclass(frozen=True)
class DateWindow:
    """C2 compound VO: the [start, end) a campaign runs over. Parses each date
    and wraps the parse failure with field context; enforces start < end as a
    construction invariant. Both are validation-kind failures."""

    _start: date
    _end: date

    @classmethod
    def from_spec(cls, spec: DateWindowSpec) -> "DateWindow":
        start = _parse_date(spec.start, field="start")
        end = _parse_date(spec.end, field="end")
        return cls(_start=start, _end=end)

    def __post_init__(self) -> None:
        if self._start >= self._end:
            raise invalid(
                "window_order",
                f"window start {self._start.isoformat()} must be before "
                f"end {self._end.isoformat()}",
                field="start",
            )

    # Safe single-representation accessors for the persistence boundary: a
    # date has exactly one representation, so exposing it is not a multi-rep leak.
    @property
    def start(self) -> date:
        return self._start

    @property
    def end(self) -> date:
        return self._end

    def __str__(self) -> str:
        return f"[{self._start.isoformat()}, {self._end.isoformat()})"


def _parse_date(value: str, *, field: str) -> date:
    try:
        return date.fromisoformat(value)  # conversion only — no rules here
    except ValueError as e:
        raise invalid("bad_date", f"invalid {field} date {value!r}", field=field) from e
