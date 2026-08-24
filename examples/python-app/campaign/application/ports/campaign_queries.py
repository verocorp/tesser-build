from __future__ import annotations

import enum
import typing

import tesser.application as ts


class CampaignViewLookup(enum.Enum):
    FOUND = "found"
    MISSING = "missing"


class LinkViewRow(ts.Response):

    def __init__(self, slug: str, target_url: str, status: str) -> None:
        self.slug = slug
        self.target_url = target_url
        self.status = status


class CampaignViewRow(ts.Response):

    def __init__(
        self,
        campaign_id: str,
        budget_amount: str,
        budget_currency: str,
        links: tuple[LinkViewRow, ...],
    ) -> None:
        self.campaign_id = campaign_id
        self.budget_amount = budget_amount
        self.budget_currency = budget_currency
        self.links = links


class FindCampaignViewRequest(ts.Request):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class FindCampaignViewResponse(ts.Response):

    def __init__(
        self, outcome: CampaignViewLookup, campaigns: tuple[CampaignViewRow, ...]
    ) -> None:
        self.outcome = outcome
        self.campaigns = campaigns


class CampaignQueries(ts.Port, typing.Protocol):

    def find_view(self, request: FindCampaignViewRequest) -> FindCampaignViewResponse: ...
