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
    """The persistence boundary for the Campaign aggregate: whole aggregate
    in, reconstructed aggregate out. Declared here, with the application
    service — the domain depends on this abstraction, never on a concrete
    store. Any object with these two methods satisfies it structurally.
    """

    def save(self, c: Campaign) -> None: ...  # whole aggregate in

    def load(self, id: CampaignID) -> Campaign: ...  # reconstructed out


class CampaignService:
    """Coordinates the link-campaign use cases. No business logic: no ``for``
    over domain objects, no arithmetic on domain quantities, no ``if`` on
    domain state — every rule lives in the ``campaign`` package.
    """

    def __init__(self, repo: CampaignRepository) -> None:
        self._repo = repo  # injected, never constructed here

    def create_campaign(self, req: CreateCampaignRequest) -> CreateCampaignResponse:
        """Create use case: Delegate constructs a brand-new aggregate."""
        spec = _to_campaign_spec(req)  # 1. Convert
        c = Campaign(spec)  # 2. Delegate (construct; raises on invalid)
        self._repo.save(c)  # 3. Persist (whole aggregate)
        return CreateCampaignResponse(  # 4. Respond (domain -> DTO)
            campaign_id=str(c.id),
            name=str(c.name),
            links=_to_short_link_views(c.links),
        )

    def add_short_link(self, req: AddShortLinkRequest) -> AddShortLinkResponse:
        """Change use case: Delegate LOADS the aggregate and calls its guarded
        transition."""
        id = CampaignID(req.campaign_id)  # 1. Convert
        c = self._repo.load(id)  # 2a. load ...
        c.add_short_link(  # 2b. ... guarded transition (raises on illegal)
            ShortLinkSpec(slug=req.slug, target_url=req.target_url, active=True)
        )
        self._repo.save(c)  # 3. Persist
        return AddShortLinkResponse(  # 4. Respond
            campaign_id=str(c.id),
            links=_to_short_link_views(c.links),
        )

    def deactivate_short_link(
        self, req: DeactivateShortLinkRequest
    ) -> DeactivateShortLinkResponse:
        """Change use case: load, then call the aggregate's guarded
        transition."""
        id = CampaignID(req.campaign_id)  # 1. Convert
        slug = Slug(req.slug)
        c = self._repo.load(id)  # 2a. load ...
        c.deactivate_short_link(slug)  # 2b. ... guarded transition
        self._repo.save(c)  # 3. Persist
        return DeactivateShortLinkResponse(  # 4. Respond
            campaign_id=str(c.id),
            links=_to_short_link_views(c.links),
        )

    def get_campaign(self, req: GetCampaignRequest) -> GetCampaignResponse:
        """Read use case: a read-only load, no transition, no persist."""
        id = CampaignID(req.campaign_id)  # 1. Convert
        c = self._repo.load(id)  # 2. Delegate (load; no transition)
        return GetCampaignResponse(  # 4. Respond
            campaign_id=str(c.id),
            name=str(c.name),
            links=_to_short_link_views(c.links),
        )


def _to_campaign_spec(req: CreateCampaignRequest) -> CampaignSpec:
    """Convert the create-campaign request DTO into a ``CampaignSpec``. Pure
    mapping — no rules — including generating a fresh campaign ID, since the
    request never supplies one."""
    links = tuple(
        ShortLinkSpec(slug=l.slug, target_url=l.target_url, active=True)
        for l in req.links
    )
    return CampaignSpec(id=_new_campaign_id_value(), name=req.name, links=links)


def _to_short_link_views(links: tuple[ShortLink, ...]) -> tuple[ShortLinkView, ...]:
    """Map the aggregate's owned short links to their response-DTO projection
    (field mapping, not a domain computation — no sum/filter/group)."""
    return tuple(
        ShortLinkView(slug=str(l.slug), target_url=str(l.target_url), active=l.active)
        for l in links
    )


def _new_campaign_id_value() -> str:
    """Generate a fresh campaign identifier. ID-generation strategy isn't
    covered by the skill; a random hex string is the simplest choice that fits
    its spirit — a stable, opaque identity assigned once, at the Convert step,
    before the aggregate is constructed."""
    return secrets.token_hex(8)
