from __future__ import annotations

import re
import datetime
import typing

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_SLUG_PATTERN: typing.Final[re.Pattern[str]] = re.compile(r"^[a-z0-9-]{4,20}$")
_LINK_STATES: typing.Final[frozenset[str]] = frozenset({"active", "inactive"})


class CampaignID(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("bad_campaign_id", "campaign id must be non-empty", field="campaign_id")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class Slug(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _SLUG_PATTERN.match(value):
            raise errors.invalid(
                "bad_slug",
                f"invalid slug {value!r}: must be 4-20 chars of lowercase "
                "letters, digits, and hyphens",
                field="slug",
            )
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not (value.startswith("http://") or value.startswith("https://")):
            raise errors.invalid(
                "bad_target_url",
                f"invalid target url {value!r}: must start with http:// or https://",
                field="target_url",
            )
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class LinkStatus(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if value not in _LINK_STATES:
            raise errors.invalid(
                "bad_link_status",
                f"invalid link status {value!r}: must be one of "
                f"{', '.join(sorted(_LINK_STATES))}",
                field="status",
            )
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class Day(ts.ValueObject):

    def __init__(self, value: str) -> None:
        try:
            parsed = datetime.date.fromisoformat(value)
        except ValueError as e:
            raise errors.invalid("bad_date", f"invalid date {value!r}") from e
        object.__setattr__(self, "_value", parsed)

    def __str__(self) -> str:
        return self._value.isoformat()

    _value: datetime.date


class DateWindowSpec(ts.Spec):

    def __init__(self, start: str, end: str) -> None:
        self.start = start
        self.end = end


class DateWindow(ts.ValueObject):

    def __init__(self, start_value: str, end_value: str) -> None:
        try:
            start = Day(start_value)
        except errors.DomainError as e:
            raise errors.wrap(e, f"invalid start date {start_value!r}", field="start") from e.__cause__
        try:
            end = Day(end_value)
        except errors.DomainError as e:
            raise errors.wrap(e, f"invalid end date {end_value!r}", field="end") from e.__cause__
        if not start._value < end._value:
            raise errors.invalid(
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
