from __future__ import annotations

import pytest

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.views as views
from tesser.errors import DomainError, Kind


def test_resolved_target_hands_back_the_url_of_an_active_link() -> None:
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

    assert views.resolved_target(found, "promo") == "https://ok.example/x"


def test_resolved_target_refuses_a_missing_lookup() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
    )

    with pytest.raises(DomainError) as caught:
        views.resolved_target(found, "promo")

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "link_missing"


def test_active_target_refuses_a_link_that_was_deactivated() -> None:
    record = campaign_repository.CampaignRecord(
        id="0123456789abcdef",
        budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
        links=(
            campaign_repository.LinkRecord(
                slug="promo",
                target_url="https://ok.example/x",
                status="inactive",
            ),
        ),
    )

    with pytest.raises(DomainError) as caught:
        views.active_target(record, "promo")

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "link_missing"


def test_active_target_refuses_a_slug_the_record_does_not_carry() -> None:
    record = campaign_repository.CampaignRecord(
        id="0123456789abcdef",
        budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
        links=(),
    )

    with pytest.raises(DomainError) as caught:
        views.active_target(record, "nosuch")

    assert caught.value.code == "link_missing"
    assert "nosuch" in caught.value.message
