from __future__ import annotations

import re
import datetime
import typing

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_SLUG_PATTERN: typing.Final[re.Pattern[str]] = re.compile(r"^[a-z0-9-]{4,20}$")
_LINK_STATES: typing.Final[frozenset[str]] = frozenset({"active", "inactive"})
_MAX_LINKS: typing.Final[int] = 5


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

    def __init__(self, spec: DateWindowSpec) -> None:
        try:
            start = Day(spec.start)
        except errors.DomainError as e:
            raise errors.wrap(e, f"invalid start date {spec.start!r}", field="start") from e.__cause__
        try:
            end = Day(spec.end)
        except errors.DomainError as e:
            raise errors.wrap(e, f"invalid end date {spec.end!r}", field="end") from e.__cause__
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


class ShortLinkSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class ShortLink(ts.Entity):

    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = Slug(spec.slug)
        self._target = TargetURL(spec.target_url)
        self._status = LinkStatus("active")

    @property
    def slug(self) -> Slug:
        return self._slug

    @property
    def target(self) -> TargetURL:
        return self._target

    @property
    def status(self) -> LinkStatus:
        return self._status

    def deactivate(self) -> None:
        if self._status == LinkStatus("inactive"):
            raise errors.conflict(
                "already_deactivated", f"short link {self._slug} is already deactivated"
            )
        self._status = LinkStatus("inactive")

    @property
    def identity(self) -> Slug:
        return self._slug


class CampaignSpec(ts.Spec):

    def __init__(
        self,
        id: str,
        window: DateWindowSpec,
        links: tuple[ShortLinkSpec, ...],
    ) -> None:
        self.id = id
        self.window = window
        self.links = links


class Campaign(ts.AggregateRoot):

    def __init__(self, spec: CampaignSpec) -> None:
        self._id = str(CampaignID(spec.id))
        self._window = DateWindow(spec.window)
        self._links: list[ShortLink] = []
        for i, link_spec in enumerate(spec.links):
            try:
                short_link = ShortLink(link_spec)
            except errors.DomainError as e:
                raise errors.wrap(e, f"link {i}: {e}", field=f"links[{i}].{e.field}") from e
            if any(existing.slug == short_link.slug for existing in self._links):
                raise errors.conflict(
                    "duplicate_slug", f"slug {short_link.slug} already in campaign {self._id}"
                )
            if len(self._links) >= _MAX_LINKS:
                raise errors.conflict(
                    "too_many_links",
                    f"campaign {self._id} is at the {_MAX_LINKS}-link cap",
                )
            self._links.append(short_link)

    def add_link(self, short_link_spec: ShortLinkSpec) -> None:
        short_link = ShortLink(short_link_spec)
        if any(existing.slug == short_link.slug for existing in self._links):
            raise errors.conflict(
                "duplicate_slug", f"slug {short_link.slug} already in campaign {self._id}"
            )
        if len(self._links) >= _MAX_LINKS:
            raise errors.conflict(
                "too_many_links",
                f"campaign {self._id} is at the {_MAX_LINKS}-link cap",
            )
        self._links.append(short_link)

    def deactivate_link(self, slug: Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise errors.not_found("link_missing", f"no link {slug} in campaign {self._id}")

    @property
    def id(self) -> str:
        return self._id

    @property
    def window(self) -> DateWindow:
        return self._window

    @property
    def links(self) -> tuple[ShortLink, ...]:
        return tuple(self._links)

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]
