import pytest

from campaign.campaign import Campaign
from campaign.campaign_id import CampaignID
from campaignapp import CampaignService
from linkcampaign import (
    AddShortLinkRequest,
    CreateCampaignRequest,
    DeactivateShortLinkRequest,
    GetCampaignRequest,
    ShortLinkInput,
)


class FakeRepo:

    def __init__(self) -> None:
        self.saved: list[Campaign] = []
        self._store: dict[str, Campaign] = {}

    def save(self, c: Campaign) -> None:
        self.saved.append(c)
        self._store[str(c.id)] = c

    def load(self, id: CampaignID) -> Campaign:
        c = self._store.get(str(id))
        if c is None:
            raise LookupError(f"campaign {id} not found")
        return c


def _create(svc: CampaignService, *slugs: str) -> str:
    resp = svc.create_campaign(
        CreateCampaignRequest(
            name="Spring",
            links=tuple(
                ShortLinkInput(slug=s, target_url="https://a.example") for s in slugs
            ),
        )
    )
    return resp.campaign_id


def test_create_campaign_constructs_and_persists() -> None:
    repo = FakeRepo()
    svc = CampaignService(repo)
    resp = svc.create_campaign(
        CreateCampaignRequest(
            name="Spring",
            links=(ShortLinkInput(slug="spring-sale", target_url="https://a.example"),),
        )
    )
    assert resp.name == "Spring"
    assert resp.campaign_id != ""
    assert resp.links[0].slug == "spring-sale"
    assert resp.links[0].active is True
    assert len(repo.saved) == 1


def test_create_campaign_rejects_invalid_domain_input() -> None:
    svc = CampaignService(FakeRepo())
    with pytest.raises(ValueError):
        svc.create_campaign(
            CreateCampaignRequest(
                name="Spring",
                links=(ShortLinkInput(slug="X", target_url="https://a.example"),),
            )
        )


def test_add_short_link_loads_transitions_saves() -> None:
    repo = FakeRepo()
    svc = CampaignService(repo)
    cid = _create(svc, "spring-sale")

    resp = svc.add_short_link(
        AddShortLinkRequest(
            campaign_id=cid, slug="autumn-sale", target_url="https://b.example"
        )
    )
    slugs = {v.slug for v in resp.links}
    assert slugs == {"spring-sale", "autumn-sale"}
    assert len(repo.saved) == 2


def test_deactivate_short_link_reflected_in_response() -> None:
    svc = CampaignService(FakeRepo())
    cid = _create(svc, "spring-sale")
    resp = svc.deactivate_short_link(
        DeactivateShortLinkRequest(campaign_id=cid, slug="spring-sale")
    )
    assert resp.links[0].active is False


def test_get_campaign_is_read_only() -> None:
    repo = FakeRepo()
    svc = CampaignService(repo)
    cid = _create(svc, "spring-sale")
    saved_before = len(repo.saved)
    resp = svc.get_campaign(GetCampaignRequest(campaign_id=cid))
    assert resp.name == "Spring"
    assert len(repo.saved) == saved_before
