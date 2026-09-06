from __future__ import annotations

import copy
import decimal
import enum
import re
import typing
import urllib.parse

import tesser.domain as ts

import campaign.domain.kernel as kernel
import tesser.errors as errors
import tesser.serialization as serialization

_CAMPAIGN_ID_RE: typing.Final[re.Pattern[str]] = re.compile(r"[a-f0-9]{16}")
_CURRENCY_RE: typing.Final[re.Pattern[str]] = re.compile(r"[A-Z]{3}")


class CampaignID(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CAMPAIGN_ID_RE.fullmatch(value):
            raise errors.invalid("invalid_campaign_id", f"campaign id {value!r} must be 16 lowercase hex chars")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class LinkState(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class LinkStatus(ts.ValueObject):

    def __init__(self, value: LinkState) -> None:
        object.__setattr__(self, "_value", value.value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class TargetURL(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if any(ord(ch) < 0x20 for ch in value):
            raise errors.invalid("invalid_target_url", "target url must not contain control characters")
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise errors.invalid("invalid_target_url", f"target url {value!r} must be http(s) with a host")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class MoneySpec(ts.Spec):

    def __init__(self, amount: str, currency: str) -> None:
        self.amount = amount
        self.currency = currency


class MoneyAmount(ts.ValueObject):

    def __init__(self, value: str) -> None:
        try:
            parsed = decimal.Decimal(value)
        except decimal.InvalidOperation as e:
            raise errors.invalid("invalid_budget_amount", f"budget amount {value!r} is not a number") from e
        if not parsed.is_finite():
            raise errors.invalid("invalid_budget_amount", f"budget amount {value!r} is not a finite number")
        if parsed < 0:
            raise errors.invalid("invalid_budget_amount", f"budget amount must not be negative: {parsed}")
        object.__setattr__(self, "_value", parsed)

    def __str__(self) -> str:
        return serialization.canonical_decimal(self._value)

    _value: decimal.Decimal


class MoneyCurrency(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CURRENCY_RE.fullmatch(value):
            raise errors.invalid("invalid_budget_currency", f"budget currency {value!r} must be 3 uppercase letters")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    _value: str


class Money(ts.ValueObject):

    def __init__(self, spec: MoneySpec) -> None:
        object.__setattr__(self, "_amount", MoneyAmount(spec.amount))
        object.__setattr__(self, "_currency", MoneyCurrency(spec.currency))

    @property
    def amount(self) -> MoneyAmount:
        return self._amount

    @property
    def currency(self) -> MoneyCurrency:
        return self._currency

    _amount: MoneyAmount
    _currency: MoneyCurrency


class ShortLinkSpec(ts.Spec):

    def __init__(self, slug: str, target_url: str, active: bool) -> None:
        self.slug = slug
        self.target_url = target_url
        self.active = active


class ShortLink(ts.Entity):

    def __init__(self, spec: ShortLinkSpec) -> None:
        self._slug = kernel.Slug(spec.slug)
        self._target_url = TargetURL(spec.target_url)
        self._status = LinkStatus(LinkState.ACTIVE if spec.active else LinkState.INACTIVE)

    @property
    def slug(self) -> kernel.Slug:
        return self._slug

    @property
    def target_url(self) -> TargetURL:
        return self._target_url

    @property
    def status(self) -> LinkStatus:
        return self._status

    def deactivate(self) -> None:
        self._status = LinkStatus(LinkState.INACTIVE)

    @property
    def identity(self) -> kernel.Slug:
        return self._slug


class ShortLinksSpec(ts.Spec):

    def __init__(self, links: tuple[ShortLinkSpec, ...]) -> None:
        self.links = links


class ShortLinks(ts.Entity):

    def __init__(self, spec: ShortLinksSpec) -> None:
        admitted: list[ShortLink] = []
        for index, link_spec in enumerate(spec.links):
            try:
                short_link = ShortLink(link_spec)
            except errors.DomainError as e:
                raise errors.invalid("invalid_short_link", f"invalid short link at index {index}: {e}") from e
            for existing in admitted:
                if existing.slug == short_link.slug:
                    raise errors.conflict("duplicate_slug", f"duplicate slug {short_link.slug} in campaign")
            admitted.append(short_link)
        self._links = admitted

    @property
    def links(self) -> tuple[ShortLink, ...]:
        return tuple(copy.copy(link) for link in self._links)

    def add(self, short_link_spec: ShortLinkSpec) -> None:
        short_link = ShortLink(short_link_spec)
        for existing in self._links:
            if existing.slug == short_link.slug:
                raise errors.conflict("duplicate_slug", f"duplicate slug {short_link.slug} in campaign")
        self._links = [*self._links, short_link]

    def deactivate(self, slug: kernel.Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise errors.not_found("link_missing", f"no short link with slug {slug}")

    def active_target(self, slug: kernel.Slug) -> TargetURL:
        link_status = LinkStatus(LinkState.ACTIVE)
        for link in self._links:
            if link.slug == slug and link.status == link_status:
                return link.target_url
        raise errors.not_found("link_missing", f"no active link for slug {slug}")


class CampaignSpec(ts.Spec):

    def __init__(self, id: str, budget: MoneySpec, links: ShortLinksSpec) -> None:
        self.id = id
        self.budget = budget
        self.links = links


class Campaign(ts.AggregateRoot):

    def __init__(self, spec: CampaignSpec) -> None:
        self._id = CampaignID(spec.id)
        self._budget = Money(spec.budget)
        self._links = ShortLinks(spec.links)

    @property
    def id(self) -> CampaignID:
        return self._id

    @property
    def budget(self) -> Money:
        return self._budget

    @property
    def links(self) -> tuple[ShortLink, ...]:
        return self._links.links

    def add_short_link(self, short_link_spec: ShortLinkSpec) -> None:
        self._links.add(short_link_spec)

    def deactivate_short_link(self, slug: kernel.Slug) -> None:
        self._links.deactivate(slug)

    def active_target(self, slug: kernel.Slug) -> TargetURL:
        return self._links.active_target(slug)

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]
