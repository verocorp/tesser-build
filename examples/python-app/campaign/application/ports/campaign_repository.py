from __future__ import annotations

import enum
import typing

import tesser.application as ts


class CampaignLookup(enum.Enum):
    FOUND = "found"
    MISSING = "missing"


class SlugAvailability(enum.Enum):
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


class FindCampaignRequest(ts.Request):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class FindCampaignBySlugRequest(ts.Request):

    def __init__(self, slug: str) -> None:
        self.slug = slug


class FindCampaignResponse(ts.Response):

    def __init__(self, outcome: CampaignLookup, campaigns: tuple[CampaignRecord, ...]) -> None:
        self.outcome = outcome
        self.campaigns = campaigns


class SlugTakenRequest(ts.Request):

    def __init__(self, slug: str) -> None:
        self.slug = slug


class SlugTakenResponse(ts.Response):

    def __init__(self, availability: SlugAvailability) -> None:
        self.availability = availability


class ListCampaignsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListCampaignsResponse(ts.Response):

    def __init__(self, campaigns: tuple[CampaignRecord, ...]) -> None:
        self.campaigns = campaigns


class CampaignRepository(ts.Port, typing.Protocol):

    def save(self, save_campaign_request: SaveCampaignRequest) -> SaveCampaignResponse: ...

    def find(self, find_campaign_request: FindCampaignRequest) -> FindCampaignResponse: ...

    def find_by_slug(self, find_campaign_by_slug_request: FindCampaignBySlugRequest) -> FindCampaignResponse: ...

    def slug_taken(self, slug_taken_request: SlugTakenRequest) -> SlugTakenResponse: ...

    def all(self, list_campaigns_request: ListCampaignsRequest) -> ListCampaignsResponse: ...
