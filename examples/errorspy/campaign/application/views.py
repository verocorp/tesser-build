from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from tesser.errors import DomainError, InfraError, not_found


@ts.do_not_use_function
def campaign_view(c: campaign.Campaign) -> client.CampaignView:
    return client.CampaignView(
        campaign_id=c.id,
        links=tuple(str(link.slug) for link in c.links),
    )


@ts.do_not_use_function
def create_spec(req: client.CreateCampaignRequest) -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id=req.campaign_id,
        window=values.DateWindowSpec(start=req.window_start, end=req.window_end),
        links=tuple(
            short_link.ShortLinkSpec(slug=link.slug, target_url=link.target_url)
            for link in req.links
        ),
    )


@ts.do_not_use_function
def save_request(c: campaign.Campaign) -> campaign_repository.SaveCampaignRequest:
    return campaign_repository.SaveCampaignRequest(
        id=c.id,
        window=_window_record(c),
        links=tuple(_link_record(link) for link in c.links),
    )


@ts.do_not_use_function
def required_campaign(
    found: campaign_repository.FindCampaignResponse, campaign_id: str
) -> campaign.Campaign:
    match found.outcome:
        case campaign_repository.CampaignLookup.FOUND:
            return rebuilt_campaign(found.campaigns[0])
        case campaign_repository.CampaignLookup.MISSING:
            raise not_found("campaign_missing", f"no campaign {campaign_id!r}")
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def rebuilt_campaign(record: campaign_repository.CampaignRecord) -> campaign.Campaign:
    try:
        return campaign.Campaign(_campaign_spec(record))
    except DomainError as e:
        raise InfraError(f"corrupted campaign record {record.id!r}: {e}") from e


@ts.do_not_use_function
def _campaign_spec(record: campaign_repository.CampaignRecord) -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id=record.id,
        window=values.DateWindowSpec(start=record.window.start, end=record.window.end),
        links=tuple(
            short_link.ShortLinkSpec(slug=link.slug, target_url=link.target_url)
            for link in record.links
        ),
    )


@ts.do_not_use_function
def _window_record(c: campaign.Campaign) -> campaign_repository.WindowRecord:
    return campaign_repository.WindowRecord(start=str(c.window.start), end=str(c.window.end))


@ts.do_not_use_function
def _link_record(link: short_link.ShortLink) -> campaign_repository.LinkRecord:
    return campaign_repository.LinkRecord(slug=str(link.slug), target_url=str(link.target))
