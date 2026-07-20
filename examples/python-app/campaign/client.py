from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CreateCampaignRequest:
    budget_amount: str
    budget_currency: str


@dataclass(frozen=True)
class AddLinkRequest:
    campaign_id: str
    slug: str
    target_url: str


@dataclass(frozen=True)
class GetCampaignRequest:
    campaign_id: str


@dataclass(frozen=True)
class ResolveRequest:
    slug: str


@dataclass(frozen=True)
class ResolveResponse:
    target_url: str


@dataclass(frozen=True)
class LinkView:
    slug: str
    target_url: str
    active: bool


@dataclass(frozen=True)
class CampaignView:
    campaign_id: str
    budget_amount: str
    budget_currency: str
    links: tuple[LinkView, ...]


@dataclass(frozen=True)
class CheckOutcome:
    allowed: bool
    reason: str


class TargetChecker(Protocol):
    def check(self, target_url: str) -> CheckOutcome: ...


class Client(Protocol):
    def create_campaign(self, req: CreateCampaignRequest) -> CampaignView: ...

    def add_link(self, req: AddLinkRequest) -> CampaignView: ...

    def get_campaign(self, req: GetCampaignRequest) -> CampaignView: ...

    def resolve(self, req: ResolveRequest) -> ResolveResponse: ...

    def list_links(self) -> tuple[LinkView, ...]: ...
