from __future__ import annotations

import pytest

import campaign.adapters.repositories as repositories
import campaign.application as application
import campaign.client as client
import storage


def test_a_missing_campaign_crosses_the_client_as_the_contexts_missing() -> None:
    campaign_service = application.CampaignService(
        repositories.StorageCampaignRepository(storage.FakeStorage())
    )
    with pytest.raises(client.Missing) as ei:
        campaign_service.get_campaign(client.GetCampaignRequest(campaign_id="missing"))
    assert ei.value.code == "campaign_missing"


def test_adding_a_link_to_a_missing_campaign_crosses_as_missing() -> None:
    campaign_service = application.CampaignService(
        repositories.StorageCampaignRepository(storage.FakeStorage())
    )
    with pytest.raises(client.Missing) as ei:
        campaign_service.add_link(
            client.AddLinkRequest(
                campaign_id="missing", slug="spring-sale", target_url="https://x.com"
            )
        )
    assert ei.value.code == "campaign_missing"
