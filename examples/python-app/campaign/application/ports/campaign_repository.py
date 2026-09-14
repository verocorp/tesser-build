from __future__ import annotations

import enum
import typing

import tesser.application as ts


class LoadCampaignOutcome(enum.Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class LoadCampaignBySlugOutcome(enum.Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class SlugTakenOutcome(enum.Enum):
    TAKEN = "taken"
    FREE = "free"


class MoneyRecord(ts.Response):

    def __init__(self, amount: str, currency: str) -> None:
        self.amount = amount
        self.currency = currency


class LinkRecord(ts.Response):

    def __init__(self, slug: str, target_url: str, status: str) -> None:
        self.slug = slug
        self.target_url = target_url
        self.status = status


class CampaignRecord(ts.Response):

    def __init__(self, id: str, budget: MoneyRecord, links: tuple[LinkRecord, ...]) -> None:
        self.id = id
        self.budget = budget
        self.links = links


class SaveCampaignRequest(ts.Request):

    def __init__(self, id: str, budget: MoneyRecord, links: tuple[LinkRecord, ...]) -> None:
        self.id = id
        self.budget = budget
        self.links = links


class SaveCampaignResponse(ts.Response):

    def __init__(self) -> None:
        return None


class LoadCampaignRequest(ts.Request):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class LoadCampaignBySlugRequest(ts.Request):

    def __init__(self, slug: str) -> None:
        self.slug = slug


class LoadCampaignResponse(ts.Response):

    def __init__(self, outcome: LoadCampaignOutcome, campaigns: tuple[CampaignRecord, ...]) -> None:
        self.outcome = outcome
        self.campaigns = campaigns


class LoadCampaignBySlugResponse(ts.Response):

    def __init__(
        self, outcome: LoadCampaignBySlugOutcome, campaigns: tuple[CampaignRecord, ...]
    ) -> None:
        self.outcome = outcome
        self.campaigns = campaigns


class SlugTakenRequest(ts.Request):

    def __init__(self, slug: str) -> None:
        self.slug = slug


class SlugTakenResponse(ts.Response):

    def __init__(self, outcome: SlugTakenOutcome) -> None:
        self.outcome = outcome


class ListCampaignsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListCampaignsResponse(ts.Response):

    def __init__(self, campaigns: tuple[CampaignRecord, ...]) -> None:
        self.campaigns = campaigns


class CampaignRepository(ts.Port, typing.Protocol):

    def save_campaign(self, save_campaign_request: SaveCampaignRequest) -> SaveCampaignResponse: ...

    def load_campaign(self, load_campaign_request: LoadCampaignRequest) -> LoadCampaignResponse: ...

    def load_campaign_by_slug(
        self, load_campaign_by_slug_request: LoadCampaignBySlugRequest
    ) -> LoadCampaignBySlugResponse: ...

    def slug_taken(self, slug_taken_request: SlugTakenRequest) -> SlugTakenResponse: ...

    def list_campaigns(self, list_campaigns_request: ListCampaignsRequest) -> ListCampaignsResponse: ...
