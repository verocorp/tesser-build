from __future__ import annotations

import tesser.domain as ts

import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.short_links as short_links
import campaign.domain.values as values
import kernel.slug as kernel_slug


class CampaignSpec(ts.Spec):

    def __init__(
        self, id: str, budget: money.MoneySpec, links: short_links.ShortLinksSpec
    ) -> None:
        self.id = id
        self.budget = budget
        self.links = links


class Campaign(ts.AggregateRoot):

    def __init__(self, spec: CampaignSpec) -> None:
        self._id = values.CampaignID(spec.id)
        self._budget = money.Money(spec.budget)
        self._links = short_links.ShortLinks(spec.links)

    @property
    def id(self) -> values.CampaignID:
        return self._id

    @property
    def budget(self) -> money.Money:
        return self._budget

    @property
    def links(self) -> tuple[short_link.ShortLink, ...]:
        return self._links.links

    def add_short_link(self, spec: short_link.ShortLinkSpec) -> None:
        self._links.add(spec)

    def deactivate_short_link(self, slug: kernel_slug.Slug) -> None:
        self._links.deactivate(slug)

    def active_target(self, slug: kernel_slug.Slug) -> values.TargetURL:
        return self._links.active_target(slug)

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]
