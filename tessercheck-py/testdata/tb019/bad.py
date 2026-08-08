from datetime import datetime
from decimal import Decimal
from enum import Enum

import tesser.domain as ts

from serialization import canonical_str


class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Slug(ts.ValueObject):

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class ShortLink(ts.Entity):

    def __init__(self, slug: str) -> None:
        self._slug = Slug(slug)
        self._active = True
        self._created = datetime.now()

    @property
    def active(self) -> bool:
        return self._active

    @property
    def status(self) -> Status:
        return Status.ACTIVE if self._active else Status.INACTIVE

    @property
    def created(self) -> datetime:
        return self._created

    def describe(self) -> str:
        return f"{self._slug}"

    def slug_pairs(self) -> tuple[tuple[str, int], ...]:
        return ((str(self._slug), 1),)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ShortLink) and self._slug == other._slug

    def __hash__(self) -> int:
        return hash(self._slug)


class Campaign(ts.AggregateRoot):

    def __init__(self, budget: str) -> None:
        self._budget = Decimal(budget)
        self._links: list[ShortLink] = []

    def total_budget(self) -> Decimal:
        return self._budget

    def link_count(self) -> int:
        return len(self._links)

    def __eq__(self, other: object) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)
