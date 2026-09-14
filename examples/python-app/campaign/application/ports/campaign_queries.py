from __future__ import annotations

import enum
import typing

import tesser.application as ts


class FindCampaignOutcome(enum.Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class Link(ts.Response):

    def __init__(self, slug: str, target_url: str, status: str) -> None:
        self.slug = slug
        self.target_url = target_url
        self.status = status


class Campaign(ts.Response):

    def __init__(
        self,
        campaign_id: str,
        budget_amount: str,
        budget_currency: str,
        links: tuple[Link, ...],
    ) -> None:
        self.campaign_id = campaign_id
        self.budget_amount = budget_amount
        self.budget_currency = budget_currency
        self.links = links


class FindCampaignRequest(ts.Request):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class FindCampaignResponse(ts.Response):

    def __init__(
        self, outcome: FindCampaignOutcome, campaigns: tuple[Campaign, ...]
    ) -> None:
        self.outcome = outcome
        self.campaigns = campaigns


class CampaignQueries(ts.Port, typing.Protocol):

    def find_campaign(self, find_campaign_request: FindCampaignRequest) -> FindCampaignResponse: ...
