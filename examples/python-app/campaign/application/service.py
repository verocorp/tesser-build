from __future__ import annotations

import secrets
from typing import Protocol

import tesser.application as ts

from campaign.application.parts import CampaignParts, CheckOutcome, FoundCampaign, MissingCampaign, campaign_parts
from campaign.application.views import active_target, campaign_view, link_view, required_campaign
from campaign.client.client import (
    AddLinkRequest,
    CampaignView,
    CreateCampaignRequest,
    DeactivateLinkRequest,
    GetCampaignRequest,
    ListLinksRequest,
    ListLinksResponse,
    ResolveRequest,
    ResolveResponse,
)
from campaign.domain.campaign import Campaign, CampaignSpec
from campaign.domain.money import MoneySpec
from campaign.domain.short_link import ShortLinkSpec
from campaign.domain.values import Slug, TargetURL
from errors import conflict, not_found


class CampaignRepository(ts.Port, Protocol):

    def save(self, parts: CampaignParts) -> None: ...

    def find(self, id: str) -> FoundCampaign | MissingCampaign: ...

    def find_by_slug(self, slug: str) -> FoundCampaign | MissingCampaign: ...

    def slug_taken(self, slug: str) -> bool: ...

    def all(self) -> tuple[CampaignParts, ...]: ...


class TargetChecker(ts.Port, Protocol):

    def check(self, target_url: str) -> CheckOutcome: ...


class CampaignService(ts.ApplicationService):

    def __init__(self, repo: CampaignRepository, checker: TargetChecker) -> None:
        self._repo = repo
        self._checker = checker

    def create_campaign(self, req: CreateCampaignRequest) -> CampaignView:
        budget = MoneySpec(amount=req.budget_amount, currency=req.budget_currency)
        c = Campaign(CampaignSpec(id=secrets.token_hex(8), budget=budget, links=()))
        self._repo.save(campaign_parts(c))
        return campaign_view(campaign_parts(c))

    def add_link(self, req: AddLinkRequest) -> CampaignView:
        slug = str(Slug(req.slug))
        outcome = self._checker.check(str(TargetURL(req.target_url)))
        if outcome.blocked():
            raise conflict("destination_blocked", f"destination not allowed: {outcome.reason}")
        if self._repo.slug_taken(slug):
            raise conflict("duplicate_slug", f"slug {req.slug!r} already exists")
        c = required_campaign(self._repo.find(req.campaign_id), req.campaign_id)
        c.add_short_link(ShortLinkSpec(slug=req.slug, target_url=req.target_url, active=True))
        self._repo.save(campaign_parts(c))
        return campaign_view(campaign_parts(c))

    def deactivate_link(self, req: DeactivateLinkRequest) -> CampaignView:
        c = required_campaign(self._repo.find(req.campaign_id), req.campaign_id)
        c.deactivate_short_link(Slug(req.slug))
        self._repo.save(campaign_parts(c))
        return campaign_view(campaign_parts(c))

    def get_campaign(self, req: GetCampaignRequest) -> CampaignView:
        c = required_campaign(self._repo.find(req.campaign_id), req.campaign_id)
        return campaign_view(campaign_parts(c))

    def resolve(self, req: ResolveRequest) -> ResolveResponse:
        slug = str(Slug(req.slug))
        match self._repo.find_by_slug(slug):
            case FoundCampaign(parts=parts):
                return ResolveResponse(target_url=active_target(parts, slug))
            case MissingCampaign():
                raise not_found("link_missing", f"no active link for slug {slug!r}")

    def list_links(self, req: ListLinksRequest) -> ListLinksResponse:
        views = tuple(link_view(link) for c in self._repo.all() for link in c.links)
        return ListLinksResponse(links=views)
