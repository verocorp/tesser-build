from __future__ import annotations

import pytest

import campaign.adapters.gateways.repo_storage as repo_storage
import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.views as views
from tesser.errors import DomainError, Kind, InfraError
from storage import FakeStorage, StorageError


def test_save_then_find_roundtrip() -> None:
    repo = repo_storage.StorageCampaignRepository(FakeStorage())
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(
                campaign_repository.LinkRecord(slug="spring-sale", target_url="https://x.com"),
            ),
        )
    )
    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    got = views.required_campaign(found, "c1")
    assert got.id == "c1"
    assert str(got.links[0].slug) == "spring-sale"


def test_missing_is_domain_not_found() -> None:
    repo = repo_storage.StorageCampaignRepository(FakeStorage())
    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="nope"))
    with pytest.raises(DomainError) as ei:
        views.required_campaign(found, "nope")
    assert ei.value.kind is Kind.NOT_FOUND
    assert ei.value.code == "campaign_missing"


def test_outage_is_infra_not_domain() -> None:
    repo = repo_storage.StorageCampaignRepository(FakeStorage(down=True))
    with pytest.raises(InfraError) as ei:
        repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    assert not isinstance(ei.value, DomainError)
    assert not isinstance(ei.value, StorageError)


def test_corrupted_record_is_infra_not_validation() -> None:
    storage = FakeStorage()
    storage.put(
        "c1",
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "BAD SLUG", "target_url": "https://x.com"}],
        },
    )
    repo = repo_storage.StorageCampaignRepository(storage)
    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    with pytest.raises(InfraError) as ei:
        views.required_campaign(found, "c1")
    assert not isinstance(ei.value, DomainError)
    assert isinstance(ei.value.__cause__, DomainError)
    assert ei.value.__cause__.kind is Kind.VALIDATION
