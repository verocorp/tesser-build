from __future__ import annotations

import tesser.application as ts

import campaign.application.parts as cparts
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from errors import DomainError, InfraError, not_found  # tessercheck:ignore TB062


@ts.function
def campaign_view(parts: cparts.CampaignParts) -> client.CampaignView:
    return client.CampaignView(
        campaign_id=parts.id,
        links=tuple(link.slug for link in parts.links),
    )


@ts.function
def create_spec(req: client.CreateCampaignRequest) -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id=req.campaign_id,
        window=values.DateWindowSpec(start=req.window_start, end=req.window_end),
        links=tuple(
            short_link.ShortLinkSpec(slug=link.slug, target_url=link.target_url)
            for link in req.links
        ),
    )


@ts.function
def campaign_spec(parts: cparts.CampaignParts) -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id=parts.id,
        window=values.DateWindowSpec(start=parts.window.start, end=parts.window.end),
        links=tuple(
            short_link.ShortLinkSpec(slug=link.slug, target_url=link.target_url)
            for link in parts.links
        ),
    )


@ts.function
def required_campaign(
    lookup: cparts.FoundCampaign | cparts.MissingCampaign, campaign_id: str
) -> campaign.Campaign:
    match lookup:
        case cparts.FoundCampaign(parts=parts):
            return rebuilt_campaign(parts)
        case cparts.MissingCampaign():
            raise not_found("campaign_missing", f"no campaign {campaign_id!r}")


@ts.function
def rebuilt_campaign(parts: cparts.CampaignParts) -> campaign.Campaign:
    try:
        return campaign.Campaign(campaign_spec(parts))
    except DomainError as e:
        raise InfraError(f"corrupted campaign record {parts.id!r}: {e}") from e
