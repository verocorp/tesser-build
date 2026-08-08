from __future__ import annotations

import tesser.application as ts

from campaign.domain.campaign import Campaign
from campaign.domain.short_link import ShortLink
from campaign.domain.values import LinkStatus


class MoneyParts(ts.Parts):

    def __init__(self, amount: str, currency: str) -> None:
        self.amount = amount
        self.currency = currency


class ShortLinkParts(ts.Parts):

    def __init__(self, slug: str, target_url: str, active: bool) -> None:
        self.slug = slug
        self.target_url = target_url
        self.active = active


class CampaignParts(ts.Parts):

    def __init__(self, id: str, budget: MoneyParts, links: tuple[ShortLinkParts, ...]) -> None:
        self.id = id
        self.budget = budget
        self.links = links


class FoundCampaign(ts.Parts):

    def __init__(self, parts: CampaignParts) -> None:
        self.parts = parts


class MissingCampaign(ts.Parts):

    def __init__(self) -> None:
        return None


class CheckOutcome(ts.Parts):

    def __init__(self, allowed: bool, reason: str) -> None:
        self.allowed = allowed
        self.reason = reason

    def blocked(self) -> bool:
        return not self.allowed


@ts.function
def campaign_parts(c: Campaign) -> CampaignParts:
    return CampaignParts(
        id=str(c.id),
        budget=MoneyParts(
            amount=str(c.budget.amount),
            currency=str(c.budget.currency),
        ),
        links=tuple(short_link_parts(link) for link in c.links),
    )


@ts.function
def short_link_parts(link: ShortLink) -> ShortLinkParts:
    return ShortLinkParts(
        slug=str(link.slug),
        target_url=str(link.target_url),
        active=link.status == LinkStatus("active"),
    )
