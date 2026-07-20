from __future__ import annotations

import secrets
from typing import Protocol

from campaign.application.parts import CampaignParts, ShortLinkParts, campaign_parts
from campaign.client import (
    AddLinkRequest,
    CampaignView,
    CreateCampaignRequest,
    GetCampaignRequest,
    LinkView,
    ResolveRequest,
    ResolveResponse,
    TargetChecker,
)
from campaign.domain.campaign import Campaign, CampaignSpec
from campaign.domain.money import MoneySpec
from campaign.domain.short_link import ShortLinkSpec
from campaign.domain.values import CampaignID, Slug, TargetURL
from errors import conflict, not_found


class CampaignRepository(Protocol):
    def save(self, c: Campaign) -> None: ...

    def find(self, id: CampaignID) -> Campaign | None: ...

    def find_by_slug(self, slug: Slug) -> Campaign | None: ...

    def all(self) -> tuple[Campaign, ...]: ...


class CampaignService:
    def __init__(self, repo: CampaignRepository, checker: TargetChecker) -> None:
        self._repo = repo
        self._checker = checker

    def create_campaign(self, req: CreateCampaignRequest) -> CampaignView:
        spec = CampaignSpec(
            id=secrets.token_hex(8),
            budget=MoneySpec(amount=req.budget_amount, currency=req.budget_currency),
            links=(),
        )
        c = Campaign(spec)
        self._repo.save(c)
        return _campaign_view(campaign_parts(c))

    def add_link(self, req: AddLinkRequest) -> CampaignView:
        c = self._find_campaign(CampaignID(req.campaign_id))
        target = TargetURL(req.target_url)
        outcome = self._checker.check(str(target))
        if not outcome.allowed:
            raise conflict("destination_blocked", f"destination not allowed: {outcome.reason}")
        slug = Slug(req.slug)
        if self._repo.find_by_slug(slug) is not None:
            raise conflict("duplicate_slug", f"slug {req.slug!r} already exists")
        c.add_short_link(ShortLinkSpec(slug=req.slug, target_url=req.target_url, active=True))
        self._repo.save(c)
        return _campaign_view(campaign_parts(c))

    def get_campaign(self, req: GetCampaignRequest) -> CampaignView:
        c = self._find_campaign(CampaignID(req.campaign_id))
        return _campaign_view(campaign_parts(c))

    def resolve(self, req: ResolveRequest) -> ResolveResponse:
        slug = Slug(req.slug)
        c = self._repo.find_by_slug(slug)
        if c is None:
            raise not_found("link_missing", f"no active link for slug {req.slug!r}")
        value = str(slug)
        parts = campaign_parts(c)
        row = next((link for link in parts.links if link.slug == value), None)
        if row is None or not row.active:
            raise not_found("link_missing", f"no active link for slug {req.slug!r}")
        return ResolveResponse(target_url=row.target_url)

    def list_links(self) -> tuple[LinkView, ...]:
        return tuple(
            _link_view(link)
            for c in self._repo.all()
            for link in campaign_parts(c).links
        )

    def _find_campaign(self, id: CampaignID) -> Campaign:
        c = self._repo.find(id)
        if c is None:
            raise not_found("campaign_missing", f"no campaign with id {id}")
        return c


def _campaign_view(parts: CampaignParts) -> CampaignView:
    return CampaignView(
        campaign_id=parts.id,
        budget_amount=parts.budget.amount,
        budget_currency=parts.budget.currency,
        links=tuple(_link_view(link) for link in parts.links),
    )


def _link_view(parts: ShortLinkParts) -> LinkView:
    return LinkView(slug=parts.slug, target_url=parts.target_url, active=parts.active)
