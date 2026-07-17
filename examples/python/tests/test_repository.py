import pytest

from campaign.campaign import Campaign, CampaignSpec
from campaign.campaign_id import CampaignID
from campaign.short_link import ShortLinkSpec
from linkcampaignimpl import InMemoryCampaignRepository


def _campaign(id: str = "c1") -> Campaign:
    return Campaign(
        CampaignSpec(
            id=id,
            name="Spring",
            links=(ShortLinkSpec(slug="spring-sale", target_url="https://a.example", active=True),),
        )
    )


def test_save_then_load_reconstructs_the_aggregate() -> None:
    repo = InMemoryCampaignRepository()
    repo.save(_campaign("c1"))

    loaded = repo.load(CampaignID("c1"))
    assert str(loaded.id) == "c1"
    assert str(loaded.name) == "Spring"
    assert str(loaded.links[0].slug) == "spring-sale"


def test_load_reruns_invariants_through_the_constructor() -> None:
    # The repository reconstructs through the Campaign constructor (spec in), so
    # a loaded aggregate is a real, invariant-checked Campaign — not a bag of
    # attributes.
    repo = InMemoryCampaignRepository()
    repo.save(_campaign("c1"))
    loaded = repo.load(CampaignID("c1"))
    # It behaves like a live aggregate: its transitions still guard.
    with pytest.raises(ValueError, match="duplicate slug"):
        loaded.add_short_link(
            ShortLinkSpec(slug="spring-sale", target_url="https://b.example", active=True)
        )


def test_load_missing_raises() -> None:
    repo = InMemoryCampaignRepository()
    with pytest.raises(LookupError, match="not found"):
        repo.load(CampaignID("nope"))
