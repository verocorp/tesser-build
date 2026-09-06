from __future__ import annotations

import typing

import tesser.context as ts


class CreateCampaignRequest(ts.Request):

    def __init__(self, budget_amount: str, budget_currency: str) -> None:
        self.budget_amount = budget_amount
        self.budget_currency = budget_currency


class AddLinkRequest(ts.Request):

    def __init__(self, campaign_id: str, slug: str, target_url: str) -> None:
        self.campaign_id = campaign_id
        self.slug = slug
        self.target_url = target_url


class DeactivateLinkRequest(ts.Request):

    def __init__(self, campaign_id: str, slug: str) -> None:
        self.campaign_id = campaign_id
        self.slug = slug


class GetCampaignRequest(ts.Request):

    def __init__(self, campaign_id: str) -> None:
        self.campaign_id = campaign_id


class ResolveRequest(ts.Request):

    def __init__(self, slug: str) -> None:
        self.slug = slug


class ResolveResponse(ts.Response):

    def __init__(self, target_url: str) -> None:
        self.target_url = target_url


class ListLinksRequest(ts.Request):

    def __init__(self) -> None:
        return None


class LinkView(ts.Response):

    def __init__(self, slug: str, target_url: str, status: str) -> None:
        self.slug = slug
        self.target_url = target_url
        self.status = status


class ListLinksResponse(ts.Response):

    def __init__(self, links: tuple[LinkView, ...]) -> None:
        self.links = links


class CampaignView(ts.Response):

    def __init__(
        self,
        campaign_id: str,
        budget_amount: str,
        budget_currency: str,
        links: tuple[LinkView, ...],
    ) -> None:
        self.campaign_id = campaign_id
        self.budget_amount = budget_amount
        self.budget_currency = budget_currency
        self.links = links


class CampaignClient(ts.Client, typing.Protocol):

    def create_campaign(self, create_campaign_request: CreateCampaignRequest) -> CampaignView: ...

    def add_link(self, add_link_request: AddLinkRequest) -> CampaignView: ...

    def deactivate_link(self, deactivate_link_request: DeactivateLinkRequest) -> CampaignView: ...

    def get_campaign(self, get_campaign_request: GetCampaignRequest) -> CampaignView: ...

    def resolve(self, resolve_request: ResolveRequest) -> ResolveResponse: ...

    def list_links(self, list_links_request: ListLinksRequest) -> ListLinksResponse: ...