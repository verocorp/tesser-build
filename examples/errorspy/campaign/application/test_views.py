from __future__ import annotations

import pytest

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.views as views
from tesser.errors import DomainError, Kind


def test_a_found_record_becomes_the_parts_a_campaign_is_rebuilt_from() -> None:
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
    mapper = views.MapToCampaignSpec(
        find_campaign_request=campaign_repository.FindCampaignRequest(campaign_id="c1"),
        found_campaign=found,
    )
    assert mapper.campaign_id == "c1"
    assert (mapper.window_start, mapper.window_end) == ("2026-01-01", "2026-02-01")
    assert tuple(
        (link_mapper.slug, link_mapper.target_url)
        for link_mapper in mapper.short_link_spec_mappers
    ) == (("spring-sale", "https://x.com"),)


def test_a_missing_outcome_is_a_not_found_naming_the_campaign() -> None:
    found = campaign_repository.FindCampaignResponse(
        outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
    )
    with pytest.raises(DomainError) as ei:
        views.MapToCampaignSpec(
            find_campaign_request=campaign_repository.FindCampaignRequest(
                campaign_id="c9"
            ),
            found_campaign=found,
        )
    assert ei.value.kind is Kind.NOT_FOUND
    assert ei.value.code == "campaign_missing"
    assert ei.value.message == "no campaign 'c9'"


def test_a_record_with_a_corrupt_slug_still_exposes_the_slug_the_repository_gave() -> None:
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
    mapper = views.MapToCampaignSpec(
        find_campaign_request=campaign_repository.FindCampaignRequest(campaign_id="c1"),
        found_campaign=found,
    )
    assert mapper.short_link_spec_mappers[0].slug == "BAD SLUG"


def test_a_sound_record_exposes_every_link_it_carried_in_order() -> None:
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
    mapper = views.MapToCampaignSpec(
        find_campaign_request=campaign_repository.FindCampaignRequest(campaign_id="c1"),
        found_campaign=found,
    )
    assert tuple(
        link_mapper.slug for link_mapper in mapper.short_link_spec_mappers
    ) == ("alpha-one", "beta-two")
