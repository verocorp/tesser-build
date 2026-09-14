from __future__ import annotations

import pytest

import campaign.adapters.repositories as repositories
import campaign.application as application
import campaign.application.ports as ports
import campaign.client as client
import tesser.errors as errors
import storage


def test_save_then_find_roundtrip() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    storage_campaign_repository.save_campaign(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(ports.LinkRecord(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    find_campaign_request = ports.FindCampaignRequest(campaign_id="c1")
    find_campaign_response = storage_campaign_repository.find_campaign(find_campaign_request)
    campaign_spec = application.MapToCampaignSpec(
        find_campaign_request=find_campaign_request,
        find_campaign_response=find_campaign_response,
    )
    assert campaign_spec.id == "c1"
    assert campaign_spec.links[0].slug == "spring-sale"


def test_a_campaign_never_saved_is_the_contexts_campaign_not_found() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    find_campaign_request = ports.FindCampaignRequest(campaign_id="nope")
    find_campaign_response = storage_campaign_repository.find_campaign(find_campaign_request)
    with pytest.raises(client.CampaignNotFound) as ei:
        application.MapToCampaignSpec(
            find_campaign_request=find_campaign_request,
            find_campaign_response=find_campaign_response,
        )
    assert ei.value.message == "no campaign 'nope'"


def test_a_corrupted_record_is_a_fault_not_a_rejection() -> None:
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
    with pytest.raises(errors.DomainError) as ei:
        campaign_service.get_campaign(client.GetCampaignRequest(campaign_id="c1"))
    assert "bad_slug" in str(ei.value)
