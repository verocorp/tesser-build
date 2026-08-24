from __future__ import annotations

import typing

import pytest

import campaign.adapters.gateways.repo_storage as repo_storage
import campaign.application.ports.campaign_repository as campaign_repository
import tesser.errors as errors
import storage


def test_a_saved_campaign_is_found_by_its_id() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(
                campaign_repository.LinkRecord(
                    slug="spring-sale", target_url="https://x.com"
                ),
            ),
        )
    )
    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    match found.outcome:
        case campaign_repository.CampaignLookup.FOUND:
            record = found.campaigns[0]
            assert record.id == "c1"
            assert (record.window.start, record.window.end) == ("2026-01-01", "2026-02-01")
            assert tuple((link.slug, link.target_url) for link in record.links) == (
                ("spring-sale", "https://x.com"),
            )
        case campaign_repository.CampaignLookup.MISSING:
            raise AssertionError("a saved campaign is served as found")
        case _ as unreachable:
            typing.assert_never(unreachable)


def test_an_id_that_was_never_saved_is_missing_and_carries_nothing() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="ghost"))
    assert (found.outcome, found.campaigns) == (
        campaign_repository.CampaignLookup.MISSING,
        (),
    )


def test_every_link_survives_the_round_trip_in_the_order_it_was_saved() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(
                campaign_repository.LinkRecord(slug="alpha-one", target_url="https://a.com"),
                campaign_repository.LinkRecord(slug="beta-two", target_url="https://b.com"),
                campaign_repository.LinkRecord(slug="gamma-three", target_url="https://c.com"),
            ),
        )
    )
    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    assert tuple(link.slug for link in found.campaigns[0].links) == (
        "alpha-one",
        "beta-two",
        "gamma-three",
    )


def test_a_campaign_with_no_links_round_trips_as_a_campaign_with_no_links() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(),
        )
    )
    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    assert found.outcome is campaign_repository.CampaignLookup.FOUND
    assert found.campaigns[0].links == ()


def test_saving_an_id_again_replaces_what_is_served() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(
                campaign_repository.LinkRecord(slug="alpha-one", target_url="https://a.com"),
            ),
        )
    )
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-03-01", end="2026-04-01"),
            links=(
                campaign_repository.LinkRecord(slug="beta-two", target_url="https://b.com"),
            ),
        )
    )
    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    record = found.campaigns[0]
    assert record.window.start == "2026-03-01"
    assert tuple(link.slug for link in record.links) == ("beta-two",)


def test_two_repositories_over_separate_storage_do_not_share_their_rows() -> None:
    first = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    second = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    first.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(),
        )
    )
    found = second.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    assert found.outcome is campaign_repository.CampaignLookup.MISSING


def test_an_outage_is_translated_into_infra_and_names_the_campaign() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage(down=True))
    with pytest.raises(errors.InfraError) as ei:
        repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    assert str(ei.value) == "storage unavailable loading campaign 'c1'"


def test_an_outage_keeps_the_storage_failure_as_the_cause() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage(down=True))
    with pytest.raises(errors.InfraError) as ei:
        repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))
    assert isinstance(ei.value.__cause__, storage.StorageUnavailable)


def test_an_outage_does_not_masquerade_as_a_missing_campaign() -> None:
    backend = storage.FakeStorage()
    repo = repo_storage.StorageCampaignRepository(backend)
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(),
        )
    )
    backend.down = True
    with pytest.raises(errors.InfraError):
        repo.find(campaign_repository.FindCampaignRequest(campaign_id="c1"))


def test_saving_answers_a_save_response() -> None:
    repo = repo_storage.StorageCampaignRepository(storage.FakeStorage())
    answered = repo.save(
        campaign_repository.SaveCampaignRequest(
            id="c1",
            window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(),
        )
    )
    assert isinstance(answered, campaign_repository.SaveCampaignResponse)
