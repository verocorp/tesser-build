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


class Problem(ts.Response):

    def __init__(self, code: str, field: str, message: str) -> None:
        self.code = code
        self.field = field
        self.message = message


class Rejection(ts.Response):

    def __init__(
        self, code: str, message: str, field: str, problems: tuple[Problem, ...]
    ) -> None:
        self.code = code
        self.message = message
        self.field = field
        self.problems = problems


class Rejected(ts.Error):

    def __init__(self, rejection: Rejection) -> None:
        super().__init__(rejection.message)
        self.rejection = rejection


class Missing(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Conflict(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Unavailable(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class Unreadable(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


ERRORS: typing.Final[
    tuple[
        type[Rejected],
        type[Missing],
        type[Conflict],
        type[Unavailable],
        type[Unreadable],
    ]
] = (Rejected, Missing, Conflict, Unavailable, Unreadable)


class CampaignClient(ts.Client, typing.Protocol):

    def create_campaign(
        self, create_campaign_request: CreateCampaignRequest
    ) -> CampaignView: ...

    def get_campaign(self, get_campaign_request: GetCampaignRequest) -> CampaignView: ...

    def add_link(self, add_link_request: AddLinkRequest) -> CampaignView: ...

    def deactivate_link(
        self, deactivate_link_request: DeactivateLinkRequest
    ) -> CampaignView: ...
