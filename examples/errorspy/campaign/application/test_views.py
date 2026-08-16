from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.views as views
import campaign.client.client as client
import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from tesser.errors import DomainError, InfraError, Kind


@ts.helper
def _spec(
    slug: str = "spring-sale",
    target_url: str = "https://x.com",
    start: str = "2026-01-01",
    end: str = "2026-02-01",
) -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id="c1",
        window=values.DateWindowSpec(start=start, end=end),
        links=(short_link.ShortLinkSpec(slug=slug, target_url=target_url),),
    )


def test_a_campaign_view_carries_the_id_and_every_slug() -> None:
    c = campaign.Campaign(
        campaign.CampaignSpec(
            id="c1",
            window=values.DateWindowSpec(start="2026-01-01", end="2026-02-01"),
            links=(
                short_link.ShortLinkSpec(slug="alpha-one", target_url="https://a.com"),
                short_link.ShortLinkSpec(slug="beta-two", target_url="https://b.com"),
            ),
        )
    )
    view = views.campaign_view(c)
    assert (view.campaign_id, view.links) == ("c1", ("alpha-one", "beta-two"))


def test_a_campaign_view_of_a_linkless_campaign_lists_nothing() -> None:
    c = campaign.Campaign(
        campaign.CampaignSpec(
            id="c1",
            window=values.DateWindowSpec(start="2026-01-01", end="2026-02-01"),
            links=(),
        )
    )
    assert views.campaign_view(c).links == ()


def test_a_deactivated_link_still_appears_in_the_view() -> None:
    c = campaign.Campaign(_spec())
    c.deactivate_link(values.Slug("spring-sale"))
    assert views.campaign_view(c).links == ("spring-sale",)


def test_a_create_request_becomes_a_spec_that_builds_the_requested_campaign() -> None:
    spec = views.create_spec(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    c = campaign.Campaign(spec)
    assert c.id == "c1"
    assert str(c.window.start) == "2026-01-01"
    assert str(c.window.end) == "2026-02-01"
    assert tuple((str(link.slug), str(link.target)) for link in c.links) == (
        ("spring-sale", "https://x.com"),
    )


def test_a_create_request_carrying_an_invalid_slug_is_refused_when_it_is_built() -> None:
    spec = views.create_spec(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="BAD", target_url="https://x.com"),),
        )
    )
    with pytest.raises(DomainError) as ei:
        campaign.Campaign(spec)
    assert ei.value.field == "links[0].slug"


def test_a_save_request_renders_the_window_and_links_as_strings() -> None:
    request = views.save_request(campaign.Campaign(_spec()))
    assert request.id == "c1"
    assert (request.window.start, request.window.end) == ("2026-01-01", "2026-02-01")
    assert tuple((link.slug, link.target_url) for link in request.links) == (
        ("spring-sale", "https://x.com"),
    )


def test_a_found_record_is_rebuilt_into_the_campaign_it_came_from() -> None:
    request = views.save_request(campaign.Campaign(_spec()))
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.FOUND,
        campaigns=(
            campaign_repository.CampaignRecord(
                id=request.id, window=request.window, links=request.links
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
    record = campaign_repository.CampaignRecord(
        id="c1",
        window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
        links=(campaign_repository.LinkRecord(slug="BAD SLUG", target_url="https://x.com"),),
    )
    with pytest.raises(InfraError) as ei:
        views.rebuilt_campaign(record)
    assert not isinstance(ei.value, DomainError)
    assert str(ei.value).startswith("corrupted campaign record 'c1': ")


def test_a_corrupt_record_keeps_the_domain_complaint_as_its_cause() -> None:
    record = campaign_repository.CampaignRecord(
        id="c1",
        window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
        links=(campaign_repository.LinkRecord(slug="BAD SLUG", target_url="https://x.com"),),
    )
    with pytest.raises(InfraError) as ei:
        views.rebuilt_campaign(record)
    cause = ei.value.__cause__
    assert isinstance(cause, DomainError)
    assert cause.kind is Kind.VALIDATION
    assert cause.code == "bad_slug"


def test_a_record_with_a_backwards_window_is_an_infrastructure_failure() -> None:
    record = campaign_repository.CampaignRecord(
        id="c1",
        window=campaign_repository.WindowRecord(start="2026-02-01", end="2026-01-01"),
        links=(),
    )
    with pytest.raises(InfraError) as ei:
        views.rebuilt_campaign(record)
    assert str(ei.value).startswith("corrupted campaign record 'c1': ")


def test_a_sound_record_is_rebuilt_without_complaint() -> None:
    record = campaign_repository.CampaignRecord(
        id="c1",
        window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
        links=(
            campaign_repository.LinkRecord(slug="alpha-one", target_url="https://a.com"),
            campaign_repository.LinkRecord(slug="beta-two", target_url="https://b.com"),
        ),
    )
    c = views.rebuilt_campaign(record)
    assert tuple(str(link.slug) for link in c.links) == ("alpha-one", "beta-two")


def test_a_campaign_survives_a_save_and_rebuild_round_trip() -> None:
    original = campaign.Campaign(
        _spec(slug="alpha-one", target_url="https://a.com", start="2026-03-01", end="2026-04-01")
    )
    request = views.save_request(original)
    rebuilt = views.rebuilt_campaign(
        campaign_repository.CampaignRecord(
            id=request.id, window=request.window, links=request.links
        )
    )
    assert rebuilt.id == "c1"
    assert rebuilt.window == original.window
    assert tuple((str(link.slug), str(link.target)) for link in rebuilt.links) == (
        ("alpha-one", "https://a.com"),
    )
