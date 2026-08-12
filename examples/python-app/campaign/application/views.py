from __future__ import annotations

import tesser.application as ts

import campaign.application.parts as cparts
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from errors import not_found  # tessercheck:ignore TB062


@ts.function
def campaign_view(parts: cparts.CampaignParts) -> client.CampaignView:
    return client.CampaignView(
        campaign_id=parts.id,
        budget_amount=parts.budget.amount,
        budget_currency=parts.budget.currency,
        links=tuple(link_view(link) for link in parts.links),
    )


@ts.function
def link_view(parts: cparts.ShortLinkParts) -> client.LinkView:
    return client.LinkView(slug=parts.slug, target_url=parts.target_url, active=parts.active)


@ts.function
def campaign_spec(parts: cparts.CampaignParts) -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id=parts.id,
        budget=money.MoneySpec(amount=parts.budget.amount, currency=parts.budget.currency),
        links=tuple(
            short_link.ShortLinkSpec(slug=link.slug, target_url=link.target_url, active=link.active)
            for link in parts.links
        ),
    )


@ts.function
def required_campaign(lookup: cparts.FoundCampaign | cparts.MissingCampaign, campaign_id: str) -> campaign.Campaign:
    id = values.CampaignID(campaign_id)
    match lookup:
        case cparts.FoundCampaign(parts=parts):
            return campaign.Campaign(campaign_spec(parts))
        case cparts.MissingCampaign():
            raise not_found("campaign_missing", f"no campaign with id {id}")


@ts.function
def active_target(parts: cparts.CampaignParts, slug: str) -> str:
    for link in parts.links:
        if link.slug == slug and link.active:
            return link.target_url
    raise not_found("link_missing", f"no active link for slug {slug!r}")
