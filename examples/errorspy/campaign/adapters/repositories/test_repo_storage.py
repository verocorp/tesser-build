from __future__ import annotations

import typing

import pytest

import campaign.adapters.repositories as repositories
import campaign.application.ports as ports
import tesser.errors as errors
import storage


def test_a_saved_campaign_is_found_by_its_id() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    storage_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(ports.LinkRecord(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    find_campaign_response = storage_campaign_repository.find(
        ports.FindCampaignRequest(campaign_id="c1")
    )
    match find_campaign_response.outcome:
        case ports.CampaignLookup.FOUND:
            record = find_campaign_response.campaigns[0]
            assert record.id == "c1"
            assert (record.window.start, record.window.end) == ("2026-01-01", "2026-02-01")
            assert tuple((link.slug, link.target_url) for link in record.links) == (
                ("spring-sale", "https://x.com"),
            )
        case ports.CampaignLookup.MISSING:
            raise AssertionError("a saved campaign is served as found")
        case _ as unreachable:
            typing.assert_never(unreachable)


def test_an_id_that_was_never_saved_is_missing_and_carries_nothing() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    find_campaign_response = storage_campaign_repository.find(
        ports.FindCampaignRequest(campaign_id="ghost")
    )
    assert (find_campaign_response.outcome, find_campaign_response.campaigns) == (
        ports.CampaignLookup.MISSING,
        (),
    )


def test_every_link_survives_the_round_trip_in_the_order_it_was_saved() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    storage_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(
                ports.LinkRecord(slug="alpha-one", target_url="https://a.com"),
                ports.LinkRecord(slug="beta-two", target_url="https://b.com"),
                ports.LinkRecord(slug="gamma-three", target_url="https://c.com"),
            ),
        )
    )
    find_campaign_response = storage_campaign_repository.find(
        ports.FindCampaignRequest(campaign_id="c1")
    )
    assert tuple(
        link.slug for link in find_campaign_response.campaigns[0].links
    ) == (
        "alpha-one",
        "beta-two",
        "gamma-three",
    )


def test_a_campaign_with_no_links_round_trips_as_a_campaign_with_no_links() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    storage_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(),
        )
    )
    find_campaign_response = storage_campaign_repository.find(
        ports.FindCampaignRequest(campaign_id="c1")
    )
    assert find_campaign_response.outcome is ports.CampaignLookup.FOUND
    assert find_campaign_response.campaigns[0].links == ()


def test_saving_an_id_again_replaces_what_is_served() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    storage_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(ports.LinkRecord(slug="alpha-one", target_url="https://a.com"),),
        )
    )
    storage_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-03-01", end="2026-04-01"),
            links=(ports.LinkRecord(slug="beta-two", target_url="https://b.com"),),
        )
    )
    find_campaign_response = storage_campaign_repository.find(
        ports.FindCampaignRequest(campaign_id="c1")
    )
    record = find_campaign_response.campaigns[0]
    assert record.window.start == "2026-03-01"
    assert tuple(link.slug for link in record.links) == ("beta-two",)


def test_two_repositories_over_separate_storage_do_not_share_their_rows() -> None:
    first = repositories.StorageCampaignRepository(storage.FakeStorage())
    second = repositories.StorageCampaignRepository(storage.FakeStorage())
    first.save(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(),
        )
    )
    find_campaign_response = second.find(ports.FindCampaignRequest(campaign_id="c1"))
    assert find_campaign_response.outcome is ports.CampaignLookup.MISSING


def test_an_outage_is_translated_into_infra_and_names_the_campaign() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage(down=True)
    )
    with pytest.raises(errors.InfraError) as ei:
        storage_campaign_repository.find(ports.FindCampaignRequest(campaign_id="c1"))
    assert str(ei.value) == "storage unavailable loading campaign 'c1'"


def test_an_outage_keeps_the_storage_failure_as_the_cause() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage(down=True)
    )
    with pytest.raises(errors.InfraError) as ei:
        storage_campaign_repository.find(ports.FindCampaignRequest(campaign_id="c1"))
    assert isinstance(ei.value.__cause__, storage.StorageUnavailable)


def test_an_outage_does_not_masquerade_as_a_missing_campaign() -> None:
    backend = storage.FakeStorage()
    storage_campaign_repository = repositories.StorageCampaignRepository(backend)
    storage_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(),
        )
    )
    backend.down = True
    with pytest.raises(errors.InfraError):
        storage_campaign_repository.find(ports.FindCampaignRequest(campaign_id="c1"))


def test_saving_answers_a_save_response() -> None:
    storage_campaign_repository = repositories.StorageCampaignRepository(
        storage.FakeStorage()
    )
    save_campaign_response = storage_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="c1",
            window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
            links=(),
        )
    )
    assert isinstance(save_campaign_response, ports.SaveCampaignResponse)
