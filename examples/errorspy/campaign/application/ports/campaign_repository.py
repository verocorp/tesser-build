from __future__ import annotations

import enum
from typing import Protocol

import tesser.application as ts


class CampaignLookup(enum.Enum):
    FOUND = "found"
    MISSING = "missing"


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

    def __init__(self, outcome: CampaignLookup, campaigns: tuple[CampaignRecord, ...]) -> None:
        self.outcome = outcome
        self.campaigns = campaigns


class CampaignRepository(ts.Port, Protocol):

    def save(self, request: SaveCampaignRequest) -> SaveCampaignResponse: ...

    def find(self, request: FindCampaignRequest) -> FindCampaignResponse: ...
