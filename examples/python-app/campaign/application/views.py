from __future__ import annotations

import typing

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
from tesser.errors import not_found


class MapToCampaignSpecFromSlugLookup(ts.Mapper):

    def __init__(
        self,
        find_campaign_by_slug_request: campaign_repository.FindCampaignBySlugRequest,
        found_campaign: campaign_repository.FindCampaignResponse,
    ) -> None:
        match found_campaign.outcome:
            case campaign_repository.CampaignLookup.FOUND:
                record = found_campaign.campaigns[0]
            case campaign_repository.CampaignLookup.MISSING:
                raise not_found(
                    "link_missing",
                    f"no active link for slug {find_campaign_by_slug_request.slug!r}",
                )
            case _ as unreachable:
                typing.assert_never(unreachable)
        self._find_campaign_by_slug_request = find_campaign_by_slug_request
        self._found_campaign = found_campaign
        self._campaign_id = record.id
        self._budget_amount = record.budget.amount
        self._budget_currency = record.budget.currency
        self._link_records = tuple(record.links)

    @property
    def find_campaign_by_slug_request(
        self,
    ) -> campaign_repository.FindCampaignBySlugRequest:
        return self._find_campaign_by_slug_request

    @property
    def found_campaign(self) -> campaign_repository.FindCampaignResponse:
        return self._found_campaign

    @property
    def campaign_id(self) -> str:
        return self._campaign_id

    @property
    def budget_amount(self) -> str:
        return self._budget_amount

    @property
    def budget_currency(self) -> str:
        return self._budget_currency

    @property
    def link_records(self) -> tuple[campaign_repository.LinkRecord, ...]:
        return self._link_records
