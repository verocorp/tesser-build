import secrets
from typing import Protocol

from campaign.campaign import Campaign, CampaignSpec
from campaign.campaign_id import CampaignID
from campaign.short_link import ShortLink, ShortLinkSpec
from campaign.slug import Slug
from linkcampaign import (
    AddShortLinkRequest,
    AddShortLinkResponse,
    CreateCampaignRequest,
    CreateCampaignResponse,
    DeactivateShortLinkRequest,
    DeactivateShortLinkResponse,
    GetCampaignRequest,
    GetCampaignResponse,
    ShortLinkView,
)


class CampaignRepository(Protocol):

    def save(self, c: Campaign) -> None: ...

    def load(self, id: CampaignID) -> Campaign: ...


class CampaignService:

    def __init__(self, repo: CampaignRepository) -> None:
        self._repo = repo

    def create_campaign(self, req: CreateCampaignRequest) -> CreateCampaignResponse:
        spec = _to_campaign_spec(req)
        c = Campaign(spec)
        self._repo.save(c)
        return CreateCampaignResponse(
            campaign_id=str(c.id),
            name=str(c.name),
            links=_to_short_link_views(c.links),
        )

    def add_short_link(self, req: AddShortLinkRequest) -> AddShortLinkResponse:
        id = CampaignID(req.campaign_id)
        c = self._repo.load(id)
        c.add_short_link(
            ShortLinkSpec(slug=req.slug, target_url=req.target_url, active=True)
        )
        self._repo.save(c)
        return AddShortLinkResponse(
            campaign_id=str(c.id),
            links=_to_short_link_views(c.links),
        )

    def deactivate_short_link(
        self, req: DeactivateShortLinkRequest
    ) -> DeactivateShortLinkResponse:
        id = CampaignID(req.campaign_id)
        slug = Slug(req.slug)
        c = self._repo.load(id)
        c.deactivate_short_link(slug)
        self._repo.save(c)
        return DeactivateShortLinkResponse(
            campaign_id=str(c.id),
            links=_to_short_link_views(c.links),
        )

    def get_campaign(self, req: GetCampaignRequest) -> GetCampaignResponse:
        id = CampaignID(req.campaign_id)
        c = self._repo.load(id)
        return GetCampaignResponse(
            campaign_id=str(c.id),
            name=str(c.name),
            links=_to_short_link_views(c.links),
        )


def _to_campaign_spec(req: CreateCampaignRequest) -> CampaignSpec:
    links = tuple(
        ShortLinkSpec(slug=l.slug, target_url=l.target_url, active=True)
        for l in req.links
    )
    return CampaignSpec(id=_new_campaign_id_value(), name=req.name, links=links)


def _to_short_link_views(links: tuple[ShortLink, ...]) -> tuple[ShortLinkView, ...]:
    return tuple(
        ShortLinkView(slug=str(l.slug), target_url=str(l.target_url), active=l.active)
        for l in links
    )


def _new_campaign_id_value() -> str:
    return secrets.token_hex(8)
