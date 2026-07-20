from __future__ import annotations

from dataclasses import dataclass

from campaign.domain.campaign import Campaign
from campaign.domain.short_link import ShortLink

@dataclass(frozen=True)
class MoneyParts:
    amount: str
    currency: str


@dataclass(frozen=True)
class ShortLinkParts:
    slug: str
    target_url: str
    active: bool


@dataclass(frozen=True)
class CampaignParts:
    id: str
    budget: MoneyParts
    links: tuple[ShortLinkParts, ...]


def campaign_parts(c: Campaign) -> CampaignParts:
    return CampaignParts(
        id=str(c.id),
        budget=MoneyParts(
            amount=str(c.budget.amount),
            currency=str(c.budget.currency),
        ),
        links=tuple(_short_link_parts(link) for link in c.links),
    )


def _short_link_parts(link: ShortLink) -> ShortLinkParts:
    return ShortLinkParts(
        slug=str(link.slug),
        target_url=str(link.target_url),
        active=link.active,
    )
