from __future__ import annotations

import tesser.application as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.views as views
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from tesser.errors import collect


class CampaignService(ts.ApplicationService):

    def __init__(self, repo: campaign_repository.CampaignRepository) -> None:
        self._repo = repo

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:
        c = campaign.Campaign(views.create_spec(req))  # tesser:debt TB082
        self._repo.save(views.save_request(c))  # tesser:debt TB082
        return views.campaign_view(c)

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))  # tesser:debt TB082
        c = views.required_campaign(found, req.campaign_id)
        return views.campaign_view(c)

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        collect(
            slug=lambda: values.Slug(req.slug),
            target_url=lambda: values.TargetURL(req.target_url),
        )
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))  # tesser:debt TB082
        c = views.required_campaign(found, req.campaign_id)
        c.add_link(short_link.ShortLinkSpec(slug=req.slug, target_url=req.target_url))
        self._repo.save(views.save_request(c))  # tesser:debt TB082
        return views.campaign_view(c)

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=req.campaign_id))  # tesser:debt TB082
        c = views.required_campaign(found, req.campaign_id)
        c.deactivate_link(values.Slug(req.slug))
        self._repo.save(views.save_request(c))  # tesser:debt TB082
        return views.campaign_view(c)
