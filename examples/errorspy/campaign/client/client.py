from __future__ import annotations

import typing

import tesser.context as ts


class LinkBody(ts.Request):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class CreateCampaignRequest(ts.Request):

    def __init__(
        self,
        campaign_id: str,
        window_start: str,
        window_end: str,
        links: tuple[LinkBody, ...],
    ) -> None:
        self.campaign_id = campaign_id
        self.window_start = window_start
        self.window_end = window_end
        self.links = links


class GetCampaignRequest(ts.Request):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class AddLinkRequest(ts.Request):

    def __init__(self, campaign_id: str, slug: str, target_url: str) -> None:
        self.campaign_id = campaign_id
        self.slug = slug
        self.target_url = target_url


class DeactivateLinkRequest(ts.Request):

    def __init__(self, campaign_id: str, slug: str) -> None:
        self.campaign_id = campaign_id
        self.slug = slug


class CampaignView(ts.Response):

    def __init__(self, campaign_id: str, links: tuple[str, ...]) -> None:
        self.campaign_id = campaign_id
        self.links = links


class Client(ts.Client, typing.Protocol):

    def create_campaign(self, req: CreateCampaignRequest) -> CampaignView: ...

    def get_campaign(self, req: GetCampaignRequest) -> CampaignView: ...

    def add_link(self, req: AddLinkRequest) -> CampaignView: ...

    def deactivate_link(self, req: DeactivateLinkRequest) -> CampaignView: ...
