from __future__ import annotations

from dataclasses import dataclass

from campaign.domain.money import Money, MoneySpec
from campaign.domain.short_link import ShortLink, ShortLinkSpec
from campaign.domain.values import CampaignID, Slug
from errors import DomainError, conflict, invalid, not_found


@dataclass(frozen=True)
class CampaignSpec:
    id: str
    budget: MoneySpec
    links: tuple[ShortLinkSpec, ...]


class Campaign:
    def __init__(self, spec: CampaignSpec) -> None:
        self._id = CampaignID(spec.id)
        self._budget = Money(spec.budget)
        admitted: list[ShortLink] = []
        for i, link_spec in enumerate(spec.links):
            try:
                link = ShortLink(link_spec)
            except DomainError as e:
                raise invalid("invalid_short_link", f"invalid short link at index {i}: {e}") from e
            admitted = _admit(admitted, link)
        self._links = admitted

    @property
    def id(self) -> CampaignID:
        return self._id

    @property
    def budget(self) -> Money:
        return self._budget

    @property
    def links(self) -> tuple[ShortLink, ...]:
        return tuple(link._clone() for link in self._links)

    def add_short_link(self, spec: ShortLinkSpec) -> None:
        self._links = _admit(self._links, ShortLink(spec))

    def deactivate_short_link(self, slug: Slug) -> None:
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise not_found("link_missing", f"no short link with slug {slug} in campaign {self._id}")

    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]


def _admit(links: list[ShortLink], link: ShortLink) -> list[ShortLink]:
    for existing in links:
        if existing.slug == link.slug:
            raise conflict("duplicate_slug", f"duplicate slug {link.slug} in campaign")
    return [*links, link]
