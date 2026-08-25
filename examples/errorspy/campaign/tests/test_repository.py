from __future__ import annotations

import pytest

import campaign.adapters.gateways.repo_storage as repo_storage
import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.service as service
import campaign.application.views as views
import campaign.client.client as client
import tesser.errors as errors
import storage


def test_save_then_find_roundtrip() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(
                campaign_repository.LinkRecord(slug="spring-sale", target_url="https://x.com"),
            ),
        )
    )
    find_campaign_request = campaign_repository.FindCampaignRequest(campaign_id="c1")
    found = repo.find(find_campaign_request)
    spec = views.MapToCampaignSpec(
        find_campaign_request=find_campaign_request, found_campaign=found
    )
    assert spec.id == "c1"
    assert spec.links[0].slug == "spring-sale"


def test_missing_is_domain_not_found() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    find_campaign_request = campaign_repository.FindCampaignRequest(campaign_id="nope")
    found = repo.find(find_campaign_request)
    with pytest.raises(errors.DomainError) as ei:
        views.MapToCampaignSpec(
            find_campaign_request=find_campaign_request, found_campaign=found
        )
    assert ei.value.kind is errors.Kind.NOT_FOUND
    assert ei.value.code == "campaign_missing"


def test_outage_is_infra_not_domain() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage(down=True))
    with pytest.raises(errors.InfraError) as ei:
        repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    assert not isinstance(ei.value, errors.DomainError)
    assert not isinstance(ei.value, storage.StorageError)


def test_corrupted_record_is_infra_not_validation() -> None:
    backend = storage.FakeStorage()
    backend.put(
        "c1",
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "BAD SLUG", "target_url": "https://x.com"}],
        },
    )
    repo = repo_storage.StorageCampaignRepository(backend)
    svc = service.CampaignService(repo)
    with pytest.raises(errors.InfraError) as ei:
        svc.get_campaign(client.GetCampaignRequest(campaign_id="c1"))
    assert not isinstance(ei.value, errors.DomainError)
    assert isinstance(ei.value.__cause__, errors.DomainError)
    assert ei.value.__cause__.kind is errors.Kind.VALIDATION
