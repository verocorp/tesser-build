from __future__ import annotations

import secrets  # tessercheck:ignore TB062
from typing import Protocol

import tesser.application as ts

import campaign.application.parts as cparts
import campaign.application.views as campaign_views
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from errors import conflict, not_found  # tessercheck:ignore TB062


class CampaignRepository(ts.Port, Protocol):

    def save(self, parts: cparts.CampaignParts) -> None: ...

    def find(self, id: str) -> cparts.FoundCampaign | cparts.MissingCampaign: ...

    def find_by_slug(self, slug: str) -> cparts.FoundCampaign | cparts.MissingCampaign: ...

    def slug_taken(self, slug: str) -> bool: ...

    def all(self) -> tuple[cparts.CampaignParts, ...]: ...


class TargetPolicy(ts.Port, Protocol):

    def check(self, target_url: str) -> cparts.PolicyOutcome: ...


class CampaignService(ts.ApplicationService):

    def __init__(self, repo: CampaignRepository, policy: TargetPolicy) -> None:
        self._repo = repo
        self._policy = policy

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:
        budget = money.MoneySpec(amount=req.budget_amount, currency=req.budget_currency)
        c = campaign.Campaign(campaign.CampaignSpec(id=secrets.token_hex(8), budget=budget, links=()))
        self._repo.save(cparts.campaign_parts(c))
        return campaign_views.campaign_view(cparts.campaign_parts(c))

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        slug = str(values.Slug(req.slug))
        outcome = self._policy.check(str(values.TargetURL(req.target_url)))
        if outcome.blocked():
            raise conflict("destination_blocked", f"destination not allowed: {outcome.reason}")
        if self._repo.slug_taken(slug):
            raise conflict("duplicate_slug", f"slug {req.slug!r} already exists")
        c = campaign_views.required_campaign(self._repo.find(req.campaign_id), req.campaign_id)
        c.add_short_link(short_link.ShortLinkSpec(slug=req.slug, target_url=req.target_url, active=True))
        self._repo.save(cparts.campaign_parts(c))
        return campaign_views.campaign_view(cparts.campaign_parts(c))

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        c = campaign_views.required_campaign(self._repo.find(req.campaign_id), req.campaign_id)
        c.deactivate_short_link(values.Slug(req.slug))
        self._repo.save(cparts.campaign_parts(c))
        return campaign_views.campaign_view(cparts.campaign_parts(c))

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        c = campaign_views.required_campaign(self._repo.find(req.campaign_id), req.campaign_id)
        return campaign_views.campaign_view(cparts.campaign_parts(c))

    def resolve(self, req: client.ResolveRequest) -> client.ResolveResponse:
        slug = str(values.Slug(req.slug))
        match self._repo.find_by_slug(slug):
            case cparts.FoundCampaign(parts=parts):
                return client.ResolveResponse(target_url=campaign_views.active_target(parts, slug))
            case cparts.MissingCampaign():
                raise not_found("link_missing", f"no active link for slug {slug!r}")

    def list_links(self, req: client.ListLinksRequest) -> client.ListLinksResponse:
        views = tuple(campaign_views.link_view(link) for c in self._repo.all() for link in c.links)
        return client.ListLinksResponse(links=views)
