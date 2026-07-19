from __future__ import annotations

from app.repository import CampaignRepository
from domain.campaign import Campaign, CampaignSpec
from domain.short_link import ShortLinkSpec
from domain.values import Slug


class CampaignService:
    def __init__(self, repo: CampaignRepository) -> None:
        self._repo = repo

    def create(self, campaign_id: str, spec: CampaignSpec) -> None:
        campaign = Campaign(campaign_id, spec)
        self._repo.save(campaign)

    def get(self, campaign_id: str) -> Campaign:
        return self._repo.get(campaign_id)

    def add_link(self, campaign_id: str, link: ShortLinkSpec) -> None:
        campaign = self._repo.get(campaign_id)
        campaign.add_link(link)
        self._repo.save(campaign)

    def deactivate_link(self, campaign_id: str, slug: str) -> None:
        campaign = self._repo.get(campaign_id)
        campaign.deactivate_link(Slug(slug))
        self._repo.save(campaign)
