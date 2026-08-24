from __future__ import annotations

import pytest

import campaign.adapters.gateways.repo_memory as repo_memory
import campaign.application.ports.campaign_repository as campaign_repository
import tesser.errors as errors


def test_a_saved_campaign_is_found_by_its_id() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
            links=(),
        )
    )

    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="0123456789abcdef"))

    assert found.outcome is campaign_repository.CampaignLookup.FOUND
    assert found.campaigns[0].budget.amount == "100.00"
    assert found.campaigns[0].budget.currency == "USD"


def test_an_unknown_id_reads_as_missing_with_no_rows() -> None:
    repo = repo_memory.InMemoryCampaignRepository()

    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="0123456789abcdef"))

    assert found.outcome is campaign_repository.CampaignLookup.MISSING
    assert found.campaigns == ()


def test_saving_the_same_id_twice_keeps_only_the_later_campaign() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
            links=(),
        )
    )
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=campaign_repository.MoneyRecord(amount="250.00", currency="EUR"),
            links=(),
        )
    )

    listed = repo.all(campaign_repository.ListCampaignsRequest())

    assert [row.budget.amount for row in listed.campaigns] == ["250.00"]


def test_a_slug_finds_the_campaign_that_owns_it() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
            links=(
                campaign_repository.LinkRecord(
                    slug="promo",
                    target_url="https://ok.example/x",
                    status="active",
                ),
            ),
        )
    )

    found = repo.find_by_slug(campaign_repository.FindCampaignBySlugRequest(slug="promo"))

    assert found.outcome is campaign_repository.CampaignLookup.FOUND
    assert found.campaigns[0].id == "0123456789abcdef"


def test_a_slug_nobody_registered_reads_as_missing() -> None:
    repo = repo_memory.InMemoryCampaignRepository()

    found = repo.find_by_slug(campaign_repository.FindCampaignBySlugRequest(slug="promo"))

    assert found.outcome is campaign_repository.CampaignLookup.MISSING
    assert found.campaigns == ()


def test_a_slug_finds_a_deactivated_link_because_the_store_does_not_judge_status() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(
        campaign_repository.SaveCampaignRequest(
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
    )

    found = repo.find_by_slug(campaign_repository.FindCampaignBySlugRequest(slug="promo"))

    assert found.outcome is campaign_repository.CampaignLookup.FOUND


def test_a_registered_slug_reads_as_taken() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
            links=(
                campaign_repository.LinkRecord(
                    slug="promo",
                    target_url="https://ok.example/x",
                    status="active",
                ),
            ),
        )
    )

    taken = repo.slug_taken(campaign_repository.SlugTakenRequest(slug="promo"))

    assert taken.availability is campaign_repository.SlugAvailability.TAKEN


def test_an_unregistered_slug_reads_as_free() -> None:
    repo = repo_memory.InMemoryCampaignRepository()

    taken = repo.slug_taken(campaign_repository.SlugTakenRequest(slug="promo"))

    assert taken.availability is campaign_repository.SlugAvailability.FREE


def test_an_empty_store_lists_no_campaigns() -> None:
    repo = repo_memory.InMemoryCampaignRepository()

    assert repo.all(campaign_repository.ListCampaignsRequest()).campaigns == ()


def test_every_saved_campaign_is_listed() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
            links=(),
        )
    )
    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="fedcba9876543210",
            budget=campaign_repository.MoneyRecord(amount="200.00", currency="USD"),
            links=(),
        )
    )

    listed = repo.all(campaign_repository.ListCampaignsRequest())

    assert sorted(row.id for row in listed.campaigns) == ["0123456789abcdef", "fedcba9876543210"]


def test_an_unavailable_store_fails_closed_on_every_read_and_write() -> None:
    repo = repo_memory.InMemoryCampaignRepository(down=True)

    with pytest.raises(errors.InfraError):
        repo.save(
            campaign_repository.SaveCampaignRequest(
                id="0123456789abcdef",
                budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
                links=(),
            )
        )
    with pytest.raises(errors.InfraError):
        repo.find(campaign_repository.FindCampaignRequest(campaign_id="0123456789abcdef"))
    with pytest.raises(errors.InfraError):
        repo.find_by_slug(campaign_repository.FindCampaignBySlugRequest(slug="promo"))
    with pytest.raises(errors.InfraError):
        repo.slug_taken(campaign_repository.SlugTakenRequest(slug="promo"))
    with pytest.raises(errors.InfraError):
        repo.all(campaign_repository.ListCampaignsRequest())


def test_closing_the_store_is_counted() -> None:
    repo = repo_memory.InMemoryCampaignRepository()

    repo.close()
    repo.close()

    assert repo.close_count == 2


def test_a_fresh_store_has_not_been_closed() -> None:
    assert repo_memory.InMemoryCampaignRepository().close_count == 0
