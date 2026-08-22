from __future__ import annotations

import pytest

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.views as views
from tesser.errors import DomainError, InfraError, Kind


def test_a_found_record_is_rebuilt_into_the_campaign_it_came_from() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id="c1",
                window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
                links=(
                    campaign_repository.LinkRecord(
                        slug="spring-sale", target_url="https://x.com"
                    ),
                ),
            ),
        ),
    )
    c = views.required_campaign(found, "c1")
    assert c.id == "c1"
    assert str(c.window.start) == "2026-01-01"
    assert tuple(str(link.slug) for link in c.links) == ("spring-sale",)


def test_a_missing_outcome_is_a_not_found_naming_the_campaign() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
    )
    with pytest.raises(DomainError) as ei:
        views.required_campaign(found, "c9")
    assert ei.value.kind is Kind.NOT_FOUND
    assert ei.value.code == "campaign_missing"
    assert ei.value.message == "no campaign 'c9'"


def test_a_record_with_a_corrupt_slug_is_an_infrastructure_failure_not_a_validation_one() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id="c1",
                window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
                links=(
                    campaign_repository.LinkRecord(
                        slug="BAD SLUG", target_url="https://x.com"
                    ),
                ),
            ),
        ),
    )
    with pytest.raises(InfraError) as ei:
        views.required_campaign(found, "c1")
    assert not isinstance(ei.value, DomainError)
    assert str(ei.value).startswith("corrupted campaign record 'c1': ")


def test_a_corrupt_record_keeps_the_domain_complaint_as_its_cause() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id="c1",
                window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
                links=(
                    campaign_repository.LinkRecord(
                        slug="BAD SLUG", target_url="https://x.com"
                    ),
                ),
            ),
        ),
    )
    with pytest.raises(InfraError) as ei:
        views.required_campaign(found, "c1")
    cause = ei.value.__cause__
    assert isinstance(cause, DomainError)
    assert cause.kind is Kind.VALIDATION
    assert cause.code == "bad_slug"


def test_a_record_with_a_backwards_window_is_an_infrastructure_failure() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id="c1",
                window=campaign_repository.WindowRecord(start="2026-02-01", end="2026-01-01"),
                links=(),
            ),
        ),
    )
    with pytest.raises(InfraError) as ei:
        views.required_campaign(found, "c1")
    assert str(ei.value).startswith("corrupted campaign record 'c1': ")


def test_a_sound_record_is_rebuilt_without_complaint() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id="c1",
                window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
                links=(
                    campaign_repository.LinkRecord(slug="alpha-one", target_url="https://a.com"),
                    campaign_repository.LinkRecord(slug="beta-two", target_url="https://b.com"),
                ),
            ),
        ),
    )
    c = views.required_campaign(found, "c1")
    assert tuple(str(link.slug) for link in c.links) == ("alpha-one", "beta-two")
