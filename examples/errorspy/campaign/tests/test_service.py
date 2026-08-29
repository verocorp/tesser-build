from __future__ import annotations

import pytest

import campaign.adapters.repositories.repo_storage as repo_storage
import campaign.application.service as service
import campaign.client.client as client
import tesser.errors as errors
import storage


def test_not_found_propagates_unwrapped_through_the_service() -> None:
    svc = service.CampaignService(repo_storage.StorageCampaignRepository(storage.FakeStorage()))
    with pytest.raises(errors.DomainError) as ei:
        svc.get_campaign(client.GetCampaignRequest(campaign_id="missing"))
    assert ei.value.kind is errors.Kind.NOT_FOUND
    assert ei.value.code == "campaign_missing"


def test_add_link_propagates_domain_not_found_for_missing_campaign() -> None:
    svc = service.CampaignService(repo_storage.StorageCampaignRepository(storage.FakeStorage()))
    with pytest.raises(errors.DomainError) as ei:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id="missing", slug="spring-sale", target_url="https://x.com"
            )
        )
    assert ei.value.code == "campaign_missing"
