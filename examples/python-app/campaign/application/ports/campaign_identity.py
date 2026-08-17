from __future__ import annotations

from typing import Protocol

import tesser.application as ts


class IssueCampaignIdentityRequest(ts.Request):

    def __init__(self) -> None:
        return None


class IssueCampaignIdentityResponse(ts.Response):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class CampaignIdentity(ts.Port, Protocol):

    def issue(self, request: IssueCampaignIdentityRequest) -> IssueCampaignIdentityResponse: ...
