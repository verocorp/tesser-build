from __future__ import annotations

import typing

import tesser.application as ts


class IssueCampaignIdentityRequest(ts.Request):

    def __init__(self) -> None:
        return None


class IssueCampaignIdentityResponse(ts.Response):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class CampaignIdentity(ts.Port, typing.Protocol):

    def issue(self, issue_campaign_identity_request: IssueCampaignIdentityRequest) -> IssueCampaignIdentityResponse: ...
