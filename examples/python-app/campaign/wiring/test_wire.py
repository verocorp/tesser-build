from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.adapters.gateways.repo_memory as repo_memory
import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.client.client as client
import campaign.wiring.config as config
import campaign.wiring.wire as wire
from tesser.errors import DomainError, Kind


@ts.fake
class FakeTargetPolicyAllowing(target_policy.TargetPolicy):

    def check(
        self, request: target_policy.CheckTargetRequest
    ) -> target_policy.CheckTargetResponse:
        return target_policy.CheckTargetResponse(
            verdict=target_policy.PolicyVerdict.ALLOWED, reason="clean"
        )


@ts.fake
class FakeTargetPolicyBlocking(target_policy.TargetPolicy):

    def check(
        self, request: target_policy.CheckTargetRequest
    ) -> target_policy.CheckTargetResponse:
        return target_policy.CheckTargetResponse(
            verdict=target_policy.PolicyVerdict.BLOCKED, reason="on the deny-list"
        )


def test_the_memory_coordinate_yields_a_working_repository() -> None:
    repo, _ = wire.repo_for(config.Config(storage="memory"))

    repo.save(
        campaign_repository.SaveCampaignRequest(
            id="0123456789abcdef",
            budget=campaign_repository.MoneyRecord(amount="100.00", currency="USD"),
            links=(),
        )
    )

    found = repo.find(campaign_repository.FindCampaignRequest(campaign_id="0123456789abcdef"))
    assert found.outcome is campaign_repository.CampaignLookup.FOUND


def test_closing_the_closeable_closes_the_repository_it_was_paired_with() -> None:
    repo, closeable = wire.repo_for(config.Config(storage="memory"))

    closeable.close()

    assert isinstance(repo, repo_memory.InMemoryCampaignRepository)
    assert repo.close_count == 1


def test_an_absent_storage_coordinate_is_refused_by_name() -> None:
    with pytest.raises(DomainError) as caught:
        wire.repo_for(config.Config(storage=""))

    assert caught.value.kind is Kind.VALIDATION
    assert caught.value.code == "missing_coordinate"


def test_an_unsupported_storage_backend_is_refused_by_name() -> None:
    with pytest.raises(DomainError) as caught:
        wire.repo_for(config.Config(storage="postgres"))

    assert caught.value.kind is Kind.VALIDATION
    assert caught.value.code == "unknown_backend"
    assert "postgres" in caught.value.message


def test_build_returns_a_client_that_serves_a_whole_campaign_round_trip() -> None:
    built, _ = wire.build(config.Config(storage="memory"), FakeTargetPolicyAllowing())

    created = built.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    built.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    assert built.resolve(client.ResolveRequest(slug="promo")).target_url == "https://ok.example/x"


def test_build_hands_the_policy_it_was_given_to_the_service() -> None:
    built, _ = wire.build(config.Config(storage="memory"), FakeTargetPolicyBlocking())
    created = built.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    with pytest.raises(DomainError) as caught:
        built.add_link(
            client.AddLinkRequest(
                campaign_id=created.campaign_id, slug="promo", target_url="https://bad.example/x"
            )
        )

    assert caught.value.code == "destination_blocked"


def test_build_refuses_an_unsupported_storage_backend_before_composing() -> None:
    with pytest.raises(DomainError) as caught:
        wire.build(config.Config(storage="redis"), FakeTargetPolicyAllowing())

    assert caught.value.code == "unknown_backend"


def test_two_builds_do_not_share_a_store() -> None:
    first, _ = wire.build(config.Config(storage="memory"), FakeTargetPolicyAllowing())
    second, _ = wire.build(config.Config(storage="memory"), FakeTargetPolicyAllowing())
    created = first.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    with pytest.raises(DomainError) as caught:
        second.get_campaign(client.GetCampaignRequest(campaign_id=created.campaign_id))

    assert caught.value.code == "campaign_missing"


def test_the_closeable_from_build_closes_the_store_it_composed() -> None:
    _, closeable = wire.build(config.Config(storage="memory"), FakeTargetPolicyAllowing())

    closeable.close()

    assert isinstance(closeable, repo_memory.InMemoryCampaignRepository)
    assert closeable.close_count == 1
