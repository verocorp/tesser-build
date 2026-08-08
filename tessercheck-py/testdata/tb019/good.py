from decimal import Decimal

import tesser.domain as ts

from serialization import canonical_decimal, canonical_int, canonical_str


class Slug(ts.ValueObject):

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class MoneyAmount(ts.ValueObject):

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", Decimal(value))

    def add(self, other: "MoneyAmount") -> "MoneyAmount":
        return MoneyAmount(str(self._value + other._value))

    def __str__(self) -> str:
        return canonical_decimal(self._value)

    _value: Decimal


class LinkStatus(ts.ValueObject):

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class LinkCount(ts.ValueObject):

    def __init__(self, value: int) -> None:
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return canonical_int(self._value)

    _value: int


class ShortLink(ts.Entity):

    def __init__(self, slug: str, status: str) -> None:
        self._slug = Slug(slug)
        self._status = LinkStatus(status)

    @property
    def slug(self) -> Slug:
        return self._slug

    @property
    def status(self) -> LinkStatus:
        return self._status

    def deactivate(self) -> None:
        self._status = LinkStatus("inactive")

    @property
    def identity(self) -> Slug:
        return self._slug


class Campaign(ts.AggregateRoot):

    def __init__(self, budget: str) -> None:
        self._budget = MoneyAmount(budget)
        self._links: list[ShortLink] = []

    @property
    def budget(self) -> MoneyAmount:
        return self._budget

    def links(self) -> tuple[ShortLink, ...]:
        return tuple(self._links)

    def link_count(self) -> LinkCount:
        return LinkCount(len(self._links))

    def add_link(self, slug: str) -> None:
        self._links.append(ShortLink(slug, "active"))

    @property
    def identity(self) -> MoneyAmount:
        return self._budget
