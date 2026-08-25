from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link
import campaign.domain.values as values
import tesser.errors as errors


class MapToShortLinkSpec(ts.Mapper, short_link.ShortLinkSpec):

    def __init__(self, link_record: campaign_repository.LinkRecord) -> None:
        super().__init__(slug=link_record.slug, target_url=link_record.target_url)


class MapToCampaignSpec(ts.Mapper, campaign.CampaignSpec):

    def __init__(
        self,
        find_campaign_request: campaign_repository.FindCampaignRequest,
        found_campaign: campaign_repository.FindCampaignResponse,
    ) -> None:
        match found_campaign.outcome:
            case campaign_repository.CampaignLookup.FOUND:
                record = found_campaign.campaigns[0]
            case campaign_repository.CampaignLookup.MISSING:
                raise errors.not_found(
                    "campaign_missing",
                    f"no campaign {find_campaign_request.campaign_id!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            id=record.id,
            window=values.DateWindowSpec(start=record.window.start, end=record.window.end),
            links=tuple(MapToShortLinkSpec(link) for link in record.links),
        )
