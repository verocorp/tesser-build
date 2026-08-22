from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from tesser.errors import DomainError, InfraError, not_found


@ts.do_not_use_function
def required_campaign(  # tesser:debt TB051
    found: campaign_repository.FindCampaignResponse, campaign_id: str
) -> campaign.Campaign:
    match found.outcome:
        case campaign_repository.CampaignLookup.FOUND:
            record = found.campaigns[0]
            spec = campaign.CampaignSpec(
                id=record.id,
                window=values.DateWindowSpec(
                    start=record.window.start, end=record.window.end
                ),
                links=tuple(
                    short_link.ShortLinkSpec(slug=link.slug, target_url=link.target_url)
                    for link in record.links
                ),
            )
            try:
                return campaign.Campaign(spec)
            except DomainError as e:
                raise InfraError(f"corrupted campaign record {record.id!r}: {e}") from e
        case campaign_repository.CampaignLookup.MISSING:
            raise not_found("campaign_missing", f"no campaign {campaign_id!r}")
        case _ as unreachable:
            typing.assert_never(unreachable)
