from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ShortLinkInput:

    slug: str
    target_url: str


@dataclass(frozen=True)
class ShortLinkView:

    slug: str
    target_url: str
    active: bool


@dataclass(frozen=True)
class CreateCampaignRequest:
    name: str
    links: tuple[ShortLinkInput, ...]


@dataclass(frozen=True)
class CreateCampaignResponse:
    campaign_id: str
    name: str
    links: tuple[ShortLinkView, ...]


@dataclass(frozen=True)
class AddShortLinkRequest:
    campaign_id: str
    slug: str
    target_url: str


@dataclass(frozen=True)
class AddShortLinkResponse:
    campaign_id: str
    links: tuple[ShortLinkView, ...]


@dataclass(frozen=True)
class DeactivateShortLinkRequest:
    campaign_id: str
    slug: str


@dataclass(frozen=True)
class DeactivateShortLinkResponse:
    campaign_id: str
    links: tuple[ShortLinkView, ...]


@dataclass(frozen=True)
class GetCampaignRequest:
    campaign_id: str


@dataclass(frozen=True)
class GetCampaignResponse:
    campaign_id: str
    name: str
    links: tuple[ShortLinkView, ...]


class Client(Protocol):

    def create_campaign(self, req: CreateCampaignRequest) -> CreateCampaignResponse: ...

    def add_short_link(self, req: AddShortLinkRequest) -> AddShortLinkResponse: ...

    def deactivate_short_link(
        self, req: DeactivateShortLinkRequest
    ) -> DeactivateShortLinkResponse: ...

    def get_campaign(self, req: GetCampaignRequest) -> GetCampaignResponse: ...
