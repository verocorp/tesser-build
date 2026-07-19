from dataclasses import dataclass

from campaign.campaign_id import CampaignID
from campaign.campaign_name import CampaignName
from campaign.short_link import ShortLink, ShortLinkSpec
from campaign.slug import Slug

MAX_SHORT_LINKS_PER_CAMPAIGN = 25


@dataclass(frozen=True)
class CampaignSpec:

    id: str
    name: str
    links: tuple[ShortLinkSpec, ...]


class Campaign:

    def __init__(self, spec: CampaignSpec) -> None:
        try:
            id = CampaignID(spec.id)
        except ValueError as e:
            raise ValueError(f"invalid campaign id: {e}") from e
        try:
            name = CampaignName(spec.name)
        except ValueError as e:
            raise ValueError(f"invalid campaign name: {e}") from e

        admitted: list[ShortLink] = []
        for i, link_spec in enumerate(spec.links):
            try:
                link = ShortLink(link_spec)
            except ValueError as e:
                raise ValueError(f"invalid short link at index {i}: {e}") from e
            admitted = _append_short_link(admitted, link)
        self._id = id
        self._name = name
        self._links = admitted

    @property
    def id(self) -> CampaignID:
        return self._id

    @property
    def name(self) -> CampaignName:
        return self._name

    @property
    def links(self) -> tuple[ShortLink, ...]:
        return tuple(link._clone() for link in self._links)

    def add_short_link(self, spec: ShortLinkSpec) -> None:
        spec = ShortLinkSpec(slug=spec.slug, target_url=spec.target_url, active=True)
        link = ShortLink(spec)
        self._links = _append_short_link(self._links, link)

    def deactivate_short_link(self, slug: Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise ValueError(f"no short link with slug {slug} in campaign {self._id}")

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]


def _append_short_link(links: list[ShortLink], link: ShortLink) -> list[ShortLink]:
    if len(links) >= MAX_SHORT_LINKS_PER_CAMPAIGN:
        raise ValueError(
            f"campaign already holds the maximum of "
            f"{MAX_SHORT_LINKS_PER_CAMPAIGN} short links"
        )
    for existing in links:
        if existing.slug == link.slug:
            raise ValueError(f"duplicate slug {link.slug} in campaign")
    return [*links, link]
