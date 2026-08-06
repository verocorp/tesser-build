from __future__ import annotations

import tesser.application as ts

from campaign.application.parts import CampaignParts, FoundCampaign, MissingCampaign, ShortLinkParts
from campaign.client import CampaignView, LinkView
from campaign.domain.campaign import Campaign, CampaignSpec
from campaign.domain.money import MoneySpec
from campaign.domain.short_link import ShortLinkSpec
from campaign.domain.values import CampaignID
from errors import not_found


@ts.function
def campaign_view(parts: CampaignParts) -> CampaignView:
    return CampaignView(
        campaign_id=parts.id,
        budget_amount=parts.budget.amount,
        budget_currency=parts.budget.currency,
        links=tuple(link_view(link) for link in parts.links),
    )


@ts.function
def link_view(parts: ShortLinkParts) -> LinkView:
    return LinkView(slug=parts.slug, target_url=parts.target_url, active=parts.active)


@ts.function
def campaign_spec(parts: CampaignParts) -> CampaignSpec:
    return CampaignSpec(
        id=parts.id,
        budget=MoneySpec(amount=parts.budget.amount, currency=parts.budget.currency),
        links=tuple(
            ShortLinkSpec(slug=link.slug, target_url=link.target_url, active=link.active)
            for link in parts.links
        ),
    )


@ts.function
def required_campaign(lookup: FoundCampaign | MissingCampaign, campaign_id: str) -> Campaign:
    id = CampaignID(campaign_id)
    match lookup:
        case FoundCampaign(parts=parts):
            return Campaign(campaign_spec(parts))
        case MissingCampaign():
            raise not_found("campaign_missing", f"no campaign with id {id}")


@ts.function
def active_target(parts: CampaignParts, slug: str) -> str:
    for link in parts.links:
        if link.slug == slug and link.active:
            return link.target_url
    raise not_found("link_missing", f"no active link for slug {slug!r}")
