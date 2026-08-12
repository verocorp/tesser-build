from __future__ import annotations

from typing import Protocol

import tesser.application as ts

import campaign.application.parts as cparts
import campaign.application.views as views
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from errors import collect  # tessercheck:ignore TB062


class CampaignRepository(ts.Port, Protocol):

    def save(self, parts: cparts.CampaignParts) -> None: ...

    def find(self, campaign_id: str) -> cparts.FoundCampaign | cparts.MissingCampaign: ...


class CampaignService(ts.ApplicationService):

    def __init__(self, repo: CampaignRepository) -> None:
        self._repo = repo

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:
        c = campaign.Campaign(views.create_spec(req))
        self._repo.save(cparts.campaign_parts(c))
        return views.campaign_view(cparts.campaign_parts(c))

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        c = views.required_campaign(self._repo.find(req.campaign_id), req.campaign_id)
        return views.campaign_view(cparts.campaign_parts(c))

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        collect(
            slug=lambda: values.Slug(req.slug),
            target_url=lambda: values.TargetURL(req.target_url),
        )
        c = views.required_campaign(self._repo.find(req.campaign_id), req.campaign_id)
        c.add_link(short_link.ShortLinkSpec(slug=req.slug, target_url=req.target_url))
        self._repo.save(cparts.campaign_parts(c))
        return views.campaign_view(cparts.campaign_parts(c))

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        c = views.required_campaign(self._repo.find(req.campaign_id), req.campaign_id)
        c.deactivate_link(values.Slug(req.slug))
        self._repo.save(cparts.campaign_parts(c))
        return views.campaign_view(cparts.campaign_parts(c))
