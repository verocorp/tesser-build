from __future__ import annotations

import tesser.domain as ts

import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from tesser.errors import DomainError, conflict, invalid, not_found


class CampaignSpec(ts.Spec):

    def __init__(self, id: str, budget: money.MoneySpec, links: tuple[short_link.ShortLinkSpec, ...]) -> None:
        self.id = id
        self.budget = budget
        self.links = links


class Campaign(ts.AggregateRoot):

    def __init__(self, spec: CampaignSpec) -> None:
        self._id = values.CampaignID(spec.id)
        self._budget = money.Money(spec.budget.amount, spec.budget.currency)
        admitted: list[short_link.ShortLink] = []
        for i, link_spec in enumerate(spec.links):
            try:
                link = short_link.ShortLink(link_spec)
            except DomainError as e:
                raise invalid("invalid_short_link", f"invalid short link at index {i}: {e}") from e
            admitted = _admit(admitted, link)
        self._links = admitted

    @property
    def id(self) -> values.CampaignID:
        return self._id

    @property
    def budget(self) -> money.Money:
        return self._budget

    @property
    def links(self) -> tuple[short_link.ShortLink, ...]:
        return tuple(link._clone() for link in self._links)

    def add_short_link(self, spec: short_link.ShortLinkSpec) -> None:
        self._links = _admit(self._links, short_link.ShortLink(spec))

    def deactivate_short_link(self, slug: values.Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise not_found("link_missing", f"no short link with slug {slug} in campaign {self._id}")

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]


@ts.function
def _admit(links: list[short_link.ShortLink], link: short_link.ShortLink) -> list[short_link.ShortLink]:
    for existing in links:
        if existing.slug == link.slug:
            raise conflict("duplicate_slug", f"duplicate slug {link.slug} in campaign")
    return [*links, link]
