from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.short_links as short_links
import campaign.domain.values as values
import tesser.errors as errors


class MapToShortLinkSpecFromRecord(ts.Mapper, short_link.ShortLinkSpec):

    def __init__(self, link_record: campaign_repository.LinkRecord) -> None:
        super().__init__(
            slug=link_record.slug,
            target_url=link_record.target_url,
            active=link_record.status == values.LinkState.ACTIVE.value,
        )


class MapToCampaignSpecFromSlugLookup(ts.Mapper, campaign.CampaignSpec):

    def __init__(
        self,
        find_campaign_by_slug_request: campaign_repository.FindCampaignBySlugRequest,
        found_campaign: campaign_repository.FindCampaignResponse,
    ) -> None:
        match found_campaign.outcome:
            case campaign_repository.CampaignLookup.FOUND:
                record = found_campaign.campaigns[0]
            case campaign_repository.CampaignLookup.MISSING:
                raise errors.not_found(
                    "link_missing",
                    f"no active link for slug {find_campaign_by_slug_request.slug!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            id=record.id,
            budget=money.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
            links=short_links.ShortLinksSpec(links=tuple(
                MapToShortLinkSpecFromRecord(link_record=link_record) for link_record in record.links
            )),
        )
