from __future__ import annotations

import pytest

import campaign.adapters.repositories as repositories
import campaign.application as application
import campaign.application.ports as ports
import campaign.client as client
import storage


def test_save_then_find_roundtrip() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    storage_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(ports.LinkRecord(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    find_campaign_request = ports.FindCampaignRequest(campaign_id="c1")
    find_campaign_response = storage_campaign_repository.find(find_campaign_request)
    campaign_spec = application.MapToCampaignSpec(
        find_campaign_request=find_campaign_request,
        find_campaign_response=find_campaign_response,
    )
    assert campaign_spec.id == "c1"
    assert campaign_spec.links[0].slug == "spring-sale"


def test_missing_is_the_contexts_missing() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    find_campaign_request = ports.FindCampaignRequest(campaign_id="nope")
    find_campaign_response = storage_campaign_repository.find(find_campaign_request)
    with pytest.raises(client.Missing) as ei:
        application.MapToCampaignSpec(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        )
    assert ei.value.code == "campaign_missing"


def test_outage_is_the_port_error_not_the_vendors() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage(down=True)
    )
    with pytest.raises(ports.StorageUnavailable) as ei:
        storage_campaign_repository.find(ports.FindCampaignRequest(campaign_id="c1"))
    assert not isinstance(ei.value, storage.StorageError)


def test_corrupted_record_is_unreadable_not_a_rejection() -> None:
    backend = storage.FakeStorage()
    backend.put(
        "c1",
        {
            "window": {"start": "2026-01-01", "end": "2026-02-01"},
            "links": [{"slug": "BAD SLUG", "target_url": "https://x.com"}],
        },
    )
    storage_campaign_repository = repositories.StorageCampaignRepository(backend)
    campaign_service = application.CampaignService(storage_campaign_repository)
    with pytest.raises(client.Unreadable) as ei:
        campaign_service.get_campaign(client.GetCampaignRequest(campaign_id="c1"))
    assert isinstance(ei.value.__cause__, Exception)
    assert "bad_slug" in str(ei.value.__cause__)
