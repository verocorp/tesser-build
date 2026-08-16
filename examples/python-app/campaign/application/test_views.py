from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.application.views as views
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
from tesser.errors import DomainError, Kind


@ts.helper
def _campaign_spec(
    id: str = "0123456789abcdef",
    amount: str = "100.00",
    currency: str = "USD",
    slug: str = "promo",
    target_url: str = "https://ok.example/x",
    active: bool = True,
) -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id=id,
        budget=money.MoneySpec(amount=amount, currency=currency),
        links=(short_link.ShortLinkSpec(slug=slug, target_url=target_url, active=active),),
    )


def test_campaign_view_carries_the_aggregate_out_as_plain_text() -> None:
    c = campaign.Campaign(_campaign_spec(id="0123456789abcdef", amount="250.00", currency="EUR"))

    view = views.campaign_view(c)

    assert view.campaign_id == "0123456789abcdef"
    assert view.budget_amount == "250.00"
    assert view.budget_currency == "EUR"


def test_campaign_view_reports_an_active_link_as_active() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo", target_url="https://ok.example/x"))

    view = views.campaign_view(c)

    assert [(link.slug, link.target_url, link.active) for link in view.links] == [
        ("promo", "https://ok.example/x", True)
    ]


def test_campaign_view_reports_a_deactivated_link_as_inactive() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo", active=False))

    view = views.campaign_view(c)

    assert [link.active for link in view.links] == [False]


def test_link_view_reports_an_active_record_as_active() -> None:
    record = campaign_repository.LinkRecord(
        slug="promo",
        target_url="https://ok.example/x",
        status=campaign_repository.LinkStatus.ACTIVE,
    )

    view = views.link_view(record)

    assert view.slug == "promo"
    assert view.target_url == "https://ok.example/x"
    assert view.active is True


def test_link_view_reports_an_inactive_record_as_inactive() -> None:
    record = campaign_repository.LinkRecord(
        slug="promo",
        target_url="https://ok.example/x",
        status=campaign_repository.LinkStatus.INACTIVE,
    )

    assert views.link_view(record).active is False


def test_save_request_carries_the_id_and_budget_of_the_aggregate() -> None:
    c = campaign.Campaign(_campaign_spec(id="fedcba9876543210", amount="7.50", currency="GBP"))

    request = views.save_request(c)

    assert request.id == "fedcba9876543210"
    assert request.budget.amount == "7.50"
    assert request.budget.currency == "GBP"


def test_save_request_records_a_deactivated_link_as_inactive() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo", active=False))

    request = views.save_request(c)

    assert [(link.slug, link.status) for link in request.links] == [
        ("promo", campaign_repository.LinkStatus.INACTIVE)
    ]


def test_save_request_records_an_active_link_as_active() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo", active=True))

    request = views.save_request(c)

    assert [link.status for link in request.links] == [campaign_repository.LinkStatus.ACTIVE]


def test_a_saved_campaign_rebuilds_into_the_same_aggregate() -> None:
    original = campaign.Campaign(_campaign_spec(amount="42.00", currency="CHF", active=False))
    request = views.save_request(original)
    record = campaign_repository.CampaignRecord(
        id=request.id, budget=request.budget, links=request.links
    )

    rebuilt = campaign.Campaign(views.campaign_spec(record))

    assert views.campaign_view(rebuilt).campaign_id == views.campaign_view(original).campaign_id
    assert rebuilt.budget == original.budget
    assert [link.status for link in rebuilt.links] == [link.status for link in original.links]


def test_required_campaign_rebuilds_the_found_record() -> None:
    request = views.save_request(campaign.Campaign(_campaign_spec(id="0123456789abcdef")))
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id=request.id, budget=request.budget, links=request.links
            ),
        ),
    )

    c = views.required_campaign(found, "0123456789abcdef")

    assert views.campaign_view(c).campaign_id == "0123456789abcdef"


def test_required_campaign_refuses_a_missing_lookup() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
    )

    with pytest.raises(DomainError) as caught:
        views.required_campaign(found, "0123456789abcdef")

    assert caught.value.kind is Kind.NOT_FOUND
    assert caught.value.code == "campaign_missing"
    assert "0123456789abcdef" in caught.value.message


def test_resolved_target_hands_back_the_url_of_an_active_link() -> None:
    request = views.save_request(
        campaign.Campaign(_campaign_spec(slug="promo", target_url="https://ok.example/x"))
    )
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id=request.id, budget=request.budget, links=request.links
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
                status=campaign_repository.LinkStatus.INACTIVE,
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


def test_ensure_target_allowed_passes_an_allowed_verdict_through() -> None:
    checked = target_policy.CheckTargetResponse(
        verdict=target_policy.PolicyVerdict.ALLOWED, reason="clean"
    )

    assert views.ensure_target_allowed(checked) is None


def test_ensure_target_allowed_turns_a_block_into_a_conflict_that_names_the_reason() -> None:
    checked = target_policy.CheckTargetResponse(
        verdict=target_policy.PolicyVerdict.BLOCKED, reason="on the deny-list"
    )

    with pytest.raises(DomainError) as caught:
        views.ensure_target_allowed(checked)

    assert caught.value.kind is Kind.CONFLICT
    assert caught.value.code == "destination_blocked"
    assert "on the deny-list" in caught.value.message


def test_ensure_slug_available_passes_a_free_slug_through() -> None:
    checked = campaign_repository.SlugTakenResponse(
        availability=campaign_repository.SlugAvailability.FREE
    )

    assert views.ensure_slug_available(checked, "promo") is None


def test_ensure_slug_available_turns_a_taken_slug_into_a_conflict() -> None:
    checked = campaign_repository.SlugTakenResponse(
        availability=campaign_repository.SlugAvailability.TAKEN
    )

    with pytest.raises(DomainError) as caught:
        views.ensure_slug_available(checked, "promo")

    assert caught.value.kind is Kind.CONFLICT
    assert caught.value.code == "duplicate_slug"
    assert "promo" in caught.value.message
