from __future__ import annotations

import pytest

import campaign.adapters.repositories as repositories
import campaign.application.ports as ports
import tesser.errors as errors


def test_a_saved_campaign_is_found_by_its_id() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    in_memory_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=ports.MoneyRecord(amount="100.00", currency="USD"),
            links=(),
        )
    )

    find_campaign_response = in_memory_campaign_repository.find(ports.FindCampaignRequest(campaign_id="0123456789abcdef"))

    assert find_campaign_response.outcome is ports.CampaignLookup.FOUND
    assert find_campaign_response.campaigns[0].budget.amount == "100.00"
    assert find_campaign_response.campaigns[0].budget.currency == "USD"


def test_an_unknown_id_reads_as_missing_with_no_rows() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()

    find_campaign_response = in_memory_campaign_repository.find(ports.FindCampaignRequest(campaign_id="0123456789abcdef"))

    assert find_campaign_response.outcome is ports.CampaignLookup.MISSING
    assert find_campaign_response.campaigns == ()


def test_saving_the_same_id_twice_keeps_only_the_later_campaign() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    in_memory_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=ports.MoneyRecord(amount="100.00", currency="USD"),
            links=(),
        )
    )
    in_memory_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=ports.MoneyRecord(amount="250.00", currency="EUR"),
            links=(),
        )
    )

    list_campaigns_response = in_memory_campaign_repository.all(ports.ListCampaignsRequest())

    assert [row.budget.amount for row in list_campaigns_response.campaigns] == ["250.00"]


def test_a_slug_finds_the_campaign_that_owns_it() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    in_memory_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=ports.MoneyRecord(amount="100.00", currency="USD"),
            links=(
                ports.LinkRecord(
                    slug="promo",
                    target_url="https://ok.example/x",
                    status="active",
                ),
            ),
        )
    )

    find_campaign_response = in_memory_campaign_repository.find_by_slug(ports.FindCampaignBySlugRequest(slug="promo"))

    assert find_campaign_response.outcome is ports.CampaignLookup.FOUND
    assert find_campaign_response.campaigns[0].id == "0123456789abcdef"


def test_a_slug_nobody_registered_reads_as_missing() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()

    find_campaign_response = in_memory_campaign_repository.find_by_slug(ports.FindCampaignBySlugRequest(slug="promo"))

    assert find_campaign_response.outcome is ports.CampaignLookup.MISSING
    assert find_campaign_response.campaigns == ()


def test_a_slug_finds_a_deactivated_link_because_the_store_does_not_judge_status() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    in_memory_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=ports.MoneyRecord(amount="100.00", currency="USD"),
            links=(
                ports.LinkRecord(
                    slug="promo",
                    target_url="https://ok.example/x",
                    status="inactive",
                ),
            ),
        )
    )

    find_campaign_response = in_memory_campaign_repository.find_by_slug(ports.FindCampaignBySlugRequest(slug="promo"))

    assert find_campaign_response.outcome is ports.CampaignLookup.FOUND


def test_a_registered_slug_reads_as_taken() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    in_memory_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=ports.MoneyRecord(amount="100.00", currency="USD"),
            links=(
                ports.LinkRecord(
                    slug="promo",
                    target_url="https://ok.example/x",
                    status="active",
                ),
            ),
        )
    )

    slug_taken_response = in_memory_campaign_repository.slug_taken(ports.SlugTakenRequest(slug="promo"))

    assert slug_taken_response.availability is ports.SlugAvailability.TAKEN


def test_an_unregistered_slug_reads_as_free() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()

    slug_taken_response = in_memory_campaign_repository.slug_taken(ports.SlugTakenRequest(slug="promo"))

    assert slug_taken_response.availability is ports.SlugAvailability.FREE


def test_an_empty_store_lists_no_campaigns() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()

    assert in_memory_campaign_repository.all(ports.ListCampaignsRequest()).campaigns == ()


def test_every_saved_campaign_is_listed() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    in_memory_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=ports.MoneyRecord(amount="100.00", currency="USD"),
            links=(),
        )
    )
    in_memory_campaign_repository.save(
        ports.SaveCampaignRequest(
            id="fedcba9876543210",
            budget=ports.MoneyRecord(amount="200.00", currency="USD"),
            links=(),
        )
    )

    list_campaigns_response = in_memory_campaign_repository.all(ports.ListCampaignsRequest())

    assert sorted(row.id for row in list_campaigns_response.campaigns) == ["0123456789abcdef", "fedcba9876543210"]


def test_an_unavailable_store_fails_closed_on_every_read_and_write() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository(down=True)

    with pytest.raises(errors.InfraError):
        in_memory_campaign_repository.save(
            ports.SaveCampaignRequest(
                id="0123456789abcdef",
                budget=ports.MoneyRecord(amount="100.00", currency="USD"),
                links=(),
            )
        )
    with pytest.raises(errors.InfraError):
        in_memory_campaign_repository.find(ports.FindCampaignRequest(campaign_id="0123456789abcdef"))
    with pytest.raises(errors.InfraError):
        in_memory_campaign_repository.find_by_slug(ports.FindCampaignBySlugRequest(slug="promo"))
    with pytest.raises(errors.InfraError):
        in_memory_campaign_repository.slug_taken(ports.SlugTakenRequest(slug="promo"))
    with pytest.raises(errors.InfraError):
        in_memory_campaign_repository.all(ports.ListCampaignsRequest())


def test_closing_the_store_is_counted() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()

    in_memory_campaign_repository.close()
    in_memory_campaign_repository.close()

    assert in_memory_campaign_repository.close_count == 2


def test_a_fresh_store_has_not_been_closed() -> None:
    assert repositories.InMemoryCampaignRepository().close_count == 0
