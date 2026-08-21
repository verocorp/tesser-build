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
        spec = views.create_spec(req)
        c = campaign.Campaign(spec)
        save_campaign_request = views.save_request(c)
        self._repo.save(save_campaign_request)
        return views.campaign_view(c)

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=campaign_id_text))
        c = views.required_campaign(found, campaign_id_text)
        return views.campaign_view(c)

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        collect(
            campaign_id=lambda: values.CampaignID(req.campaign_id),
            slug=lambda: values.Slug(req.slug),
            target_url=lambda: values.TargetURL(req.target_url),
        )
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=campaign_id_text))
        c = views.required_campaign(found, campaign_id_text)
        c.add_link(short_link.ShortLinkSpec(slug=req.slug, target_url=req.target_url))
        save_campaign_request = views.save_request(c)
        self._repo.save(save_campaign_request)
        return views.campaign_view(c)

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        campaign_id = values.CampaignID(req.campaign_id)
        campaign_id_text = str(campaign_id)
        found = self._repo.find(campaign_repository.FindCampaignRequest(campaign_id=campaign_id_text))
        c = views.required_campaign(found, campaign_id_text)
        c.deactivate_link(values.Slug(req.slug))
        save_campaign_request = views.save_request(c)
        self._repo.save(save_campaign_request)
        return views.campaign_view(c)
