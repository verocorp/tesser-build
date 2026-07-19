from dataclasses import dataclass

from campaign.campaign import Campaign, CampaignSpec
from campaign.campaign_id import CampaignID
from campaign.short_link import ShortLinkSpec


@dataclass(frozen=True)
class _LinkRecord:

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

    def __init__(self) -> None:
        self._campaigns: dict[str, _CampaignRecord] = {}

    def save(self, c: Campaign) -> None:
        self._campaigns[str(c.id)] = _decompose(c)

    def load(self, id: CampaignID) -> Campaign:
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
