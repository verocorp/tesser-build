"""The application service: orchestration only (convert -> delegate -> persist).

X2: it does NOT wrap domain or repo errors with "failed to ..." context. Those
errors already carry their kind, code, and field, so re-wrapping would only add
noise and bury the identity the boundary needs. Errors propagate untouched.
"""

from __future__ import annotations

from app.repository import CampaignRepository
from domain.campaign import Campaign, CampaignSpec
from domain.short_link import ShortLinkSpec
from domain.values import Slug


class CampaignService:
    def __init__(self, repo: CampaignRepository) -> None:
        self._repo = repo

    def create(self, campaign_id: str, spec: CampaignSpec) -> None:
        campaign = Campaign(campaign_id, spec)  # validation happens in the domain
        self._repo.save(campaign)

    def get(self, campaign_id: str) -> Campaign:
        return self._repo.get(campaign_id)  # not_found / infra propagate

    def add_link(self, campaign_id: str, link: ShortLinkSpec) -> None:
        campaign = self._repo.get(campaign_id)  # not_found propagates
        campaign.add_link(link)  # validation / conflict propagate
        self._repo.save(campaign)

    def deactivate_link(self, campaign_id: str, slug: str) -> None:
        campaign = self._repo.get(campaign_id)
        campaign.deactivate_link(Slug(slug))  # slug validation + not_found / conflict
        self._repo.save(campaign)
