from __future__ import annotations

import pytest

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.views as views
from tesser.errors import DomainError, Kind


def test_a_found_slug_lookup_exposes_the_parts_the_campaign_is_rebuilt_from() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id="0123456789abcdef",
                budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
                links=(
                    campaign_repository.LinkRecord(
                        slug="promo", target_url="https://ok.example/x", status="active"
                    ),
                ),
            ),
        ),
    )

    mapper = views.MapToCampaignSpecFromSlugLookup(
        find_campaign_by_slug_request=campaign_repository.FindCampaignBySlugRequest(
            slug="promo"
        ),
        found_campaign=found,
    )

    assert mapper.campaign_id == "0123456789abcdef"
    assert (mapper.budget_amount, mapper.budget_currency) == ("100.00", "USD")
    assert tuple(
        (link.slug, link.target_url, link.status) for link in mapper.link_records
    ) == (("promo", "https://ok.example/x", "active"),)


def test_a_missing_slug_lookup_is_refused_before_anything_is_rebuilt() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
    )

    with pytest.raises(DomainError) as caught:
        views.MapToCampaignSpecFromSlugLookup(
            find_campaign_by_slug_request=campaign_repository.FindCampaignBySlugRequest(
                slug="promo"
            ),
            found_campaign=found,
        )

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "link_missing"
    assert "promo" in caught.value.message


def test_a_deactivated_link_still_reaches_the_mapper_because_the_store_does_not_judge() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id="0123456789abcdef",
                budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
                links=(
                    campaign_repository.LinkRecord(
                        slug="promo",
                        target_url="https://ok.example/x",
                        status="inactive",
                    ),
                ),
            ),
        ),
    )

    mapper = views.MapToCampaignSpecFromSlugLookup(
        find_campaign_by_slug_request=campaign_repository.FindCampaignBySlugRequest(
            slug="promo"
        ),
        found_campaign=found,
    )

    assert mapper.link_records[0].status == "inactive"
