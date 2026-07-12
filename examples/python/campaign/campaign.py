from dataclasses import dataclass

from campaign.campaign_id import CampaignID
from campaign.campaign_name import CampaignName
from campaign.short_link import ShortLink, ShortLinkSpec
from campaign.slug import Slug

# MAX_SHORT_LINKS_PER_CAMPAIGN is the business rule capping how many short
# links one campaign may hold.
MAX_SHORT_LINKS_PER_CAMPAIGN = 25


@dataclass(frozen=True)
class CampaignSpec:
    """Carries construction data across the layer boundary: primitive leaves,
    with nesting mirroring composition — ``links`` holds nested
    ``ShortLinkSpec`` values, never flattened prefixed fields.
    """

    id: str
    name: str
    links: tuple[ShortLinkSpec, ...]


class Campaign:
    """The aggregate root: it owns a set of ShortLinks and enforces the
    invariants that span them — no two short links may share a slug, and a
    campaign holds at most ``MAX_SHORT_LINKS_PER_CAMPAIGN`` links. It is the
    only entry point for adding or deactivating an owned short link; nothing
    outside the aggregate holds or mutates the collection directly.

    A campaign has a lifecycle (links are added and deactivated over time), so
    it is a mutable aggregate: root-guarded transitions re-establish the
    invariants after every change.
    """

    def __init__(self, id: CampaignID, name: CampaignName, links: list[ShortLink]) -> None:
        # The cross-object invariants are enforced here, so an invalid Campaign
        # is unrepresentable regardless of the construction path.
        admitted: list[ShortLink] = []
        for link in links:
            admitted = _append_short_link(admitted, link)
        self._id = id
        self._name = name
        self._links = admitted  # own your copy

    @classmethod
    def from_spec(cls, spec: CampaignSpec) -> "Campaign":
        """Validate and construct a Campaign, including its initial — possibly
        empty — set of short links."""
        try:
            id = CampaignID(spec.id)
        except ValueError as e:
            raise ValueError(f"invalid campaign id: {e}") from e
        try:
            name = CampaignName(spec.name)
        except ValueError as e:
            raise ValueError(f"invalid campaign name: {e}") from e

        links: list[ShortLink] = []
        for i, link_spec in enumerate(spec.links):
            try:
                links.append(ShortLink.from_spec(link_spec))
            except ValueError as e:
                raise ValueError(f"invalid short link at index {i}: {e}") from e
        return cls(id, name, links)

    @property
    def id(self) -> CampaignID:
        return self._id

    @property
    def name(self) -> CampaignName:
        return self._name

    @property
    def links(self) -> tuple[ShortLink, ...]:
        # Defensive copy out — the caller can never mutate the campaign's owned
        # collection.
        return tuple(self._links)

    def add_short_link(self, spec: ShortLinkSpec) -> None:
        """Root-guarded transition for the "add a short link to an existing
        campaign" use case: re-establishes both cross-object invariants (unique
        slug, at-most-max links) before the new link is admitted."""
        spec = ShortLinkSpec(slug=spec.slug, target_url=spec.target_url, active=True)
        link = ShortLink.from_spec(spec)
        self._links = _append_short_link(self._links, link)

    def deactivate_short_link(self, slug: Slug) -> None:
        """Root-guarded transition for the "deactivate a short link" use case:
        the root looks up the owned child by its slug and calls its guarded
        lifecycle method — callers never reach into the collection themselves."""
        for link in self._links:
            if link.slug == slug:
                link.deactivate()
                return
        raise ValueError(f"no short link with slug {slug} in campaign {self._id}")

    # Comparing aggregates by value is a bug — an aggregate has identity and a
    # lifecycle, not value semantics. Setting these to None makes ``==`` raise
    # TypeError and instances unhashable, the closest Python gets to Go's
    # compile-time non-comparability.
    __eq__ = None  # type: ignore[assignment]
    __hash__ = None  # type: ignore[assignment]


def _append_short_link(links: list[ShortLink], link: ShortLink) -> list[ShortLink]:
    """Enforces the invariants that span the campaign's owned short links — no
    two links may share a slug, and a campaign holds at most
    ``MAX_SHORT_LINKS_PER_CAMPAIGN`` links. Shared by the constructor and
    ``add_short_link`` so the rule is enforced in exactly one place, never by
    callers.
    """
    if len(links) >= MAX_SHORT_LINKS_PER_CAMPAIGN:
        raise ValueError(
            f"campaign already holds the maximum of "
            f"{MAX_SHORT_LINKS_PER_CAMPAIGN} short links"
        )
    for existing in links:
        if existing.slug == link.slug:
            raise ValueError(f"duplicate slug {link.slug} in campaign")
    return [*links, link]
