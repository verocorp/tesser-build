from __future__ import annotations

import enum
import typing

import tesser.application as ts


class FindCampaignOutcome(enum.Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class WindowRecord(ts.Response):

    def __init__(self, start: str, end: str) -> None:
        self.start = start
        self.end = end


class LinkRecord(ts.Response):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class CampaignRecord(ts.Response):

    def __init__(self, id: str, window: WindowRecord, links: tuple[LinkRecord, ...]) -> None:
        self.id = id
        self.window = window
        self.links = links


class SaveCampaignRequest(ts.Request):

    def __init__(self, id: str, window: WindowRecord, links: tuple[LinkRecord, ...]) -> None:
        self.id = id
        self.window = window
        self.links = links


class SaveCampaignResponse(ts.Response):

    def __init__(self) -> None:
        return None


class FindCampaignRequest(ts.Request):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class FindCampaignResponse(ts.Response):

    def __init__(self, outcome: FindCampaignOutcome, campaigns: tuple[CampaignRecord, ...]) -> None:
        self.outcome = outcome
        self.campaigns = campaigns


class CampaignRepository(ts.Port, typing.Protocol):

    def save_campaign(
        self, save_campaign_request: SaveCampaignRequest
    ) -> SaveCampaignResponse: ...

    def find_campaign(
        self, find_campaign_request: FindCampaignRequest
    ) -> FindCampaignResponse: ...
