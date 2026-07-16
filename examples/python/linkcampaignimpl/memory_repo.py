from dataclasses import dataclass

from campaign.campaign import Campaign, CampaignSpec
from campaign.campaign_id import CampaignID
from campaign.short_link import ShortLinkSpec


@dataclass(frozen=True)
class _LinkRecord:
    """A storage row: primitive leaves, shaped by persistence rather than the
    domain."""

    slug: str
    target_url: str
    active: bool


@dataclass(frozen=True)
class _CampaignRecord:
    id: str
    name: str
    links: tuple[_LinkRecord, ...]

    def to_spec(self) -> CampaignSpec:
        return CampaignSpec(
            id=self.id,
            name=self.name,
            links=tuple(
                ShortLinkSpec(slug=l.slug, target_url=l.target_url, active=l.active)
                for l in self.links
            ),
        )


class InMemoryCampaignRepository:
    """An in-memory ``campaignapp.CampaignRepository`` — fine for tests and
    this runnable example. A database-backed repository would satisfy the same
    Protocol later; swapping it in is a one-line change at the composition
    root.
    """

    def __init__(self) -> None:
        self._campaigns: dict[str, _CampaignRecord] = {}

    def save(self, c: Campaign) -> None:
        # Take the whole aggregate and decompose it into a storage row — the
        # caller never extracts children itself.
        self._campaigns[str(c.id)] = _decompose(c)

    def load(self, id: CampaignID) -> Campaign:
        # Reconstruct the aggregate through its constructor, so every invariant
        # is re-established on the way out; a stored-but-invalid aggregate
        # cannot come back to life.
        rec = self._campaigns.get(str(id))
        if rec is None:
            raise LookupError(f"campaign {id} not found")
        return Campaign(rec.to_spec())


def _decompose(c: Campaign) -> _CampaignRecord:
    return _CampaignRecord(
        id=str(c.id),
        name=str(c.name),
        links=tuple(
            _LinkRecord(slug=str(l.slug), target_url=str(l.target_url), active=l.active)
            for l in c.links
        ),
    )
