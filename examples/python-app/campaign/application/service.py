from __future__ import annotations

import secrets  # tessercheck:ignore TB062

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.application.views as campaign_views
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.values as values


class CampaignService(ts.ApplicationService):

    def __init__(
        self,
        repo: campaign_repository.CampaignRepository,
        policy: target_policy.TargetPolicy,
    ) -> None:
        self._repo = repo
        self._policy = policy

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:
        budget = money.MoneySpec(amount=req.budget_amount, currency=req.budget_currency)
        c = campaign.Campaign(campaign.CampaignSpec(id=secrets.token_hex(8), budget=budget, links=()))
        self._repo.save(campaign_views.save_request(c))
        return campaign_views.campaign_view(c)

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        slug = str(values.Slug(req.slug))
        target_url = str(values.TargetURL(req.target_url))
        campaign_views.ensure_target_allowed(self._policy.check(target_policy.CheckTargetRequest(target_url=target_url)))
        campaign_views.ensure_slug_available(self._repo.slug_taken(campaign_repository.SlugTakenRequest(slug=slug)), slug)
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))
        c = campaign_views.required_campaign(found, req.campaign_id)
        c.add_short_link(short_link.ShortLinkSpec(slug=req.slug, target_url=req.target_url, active=True))
        self._repo.save(campaign_views.save_request(c))
        return campaign_views.campaign_view(c)

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))
        c = campaign_views.required_campaign(found, req.campaign_id)
        c.deactivate_short_link(values.Slug(req.slug))
        self._repo.save(campaign_views.save_request(c))
        return campaign_views.campaign_view(c)

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))
        c = campaign_views.required_campaign(found, req.campaign_id)
        return campaign_views.campaign_view(c)

    def resolve(self, req: client.ResolveRequest) -> client.ResolveResponse:
        slug = str(values.Slug(req.slug))
        found = self._repo.find_by_slug(campaign_repository.FindCampaignBySlugRequest(slug=slug))
        return client.ResolveResponse(target_url=campaign_views.resolved_target(found, slug))

    def list_links(self, req: client.ListLinksRequest) -> client.ListLinksResponse:
        listed = self._repo.all(campaign_repository.ListCampaignsRequest())
        views = tuple(
            campaign_views.link_view(link) for c in listed.campaigns for link in c.links
        )
        return client.ListLinksResponse(links=views)
