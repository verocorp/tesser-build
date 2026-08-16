from __future__ import annotations

import pytest
import tesser.testing as ts

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


def test_an_absent_storage_coordinate_is_refused_by_name() -> None:
    with pytest.raises(DomainError) as caught:
        wire.Campaign(config.Config(config.Spec(storage="")), FakeTargetPolicyAllowing())

    assert caught.value.kind is Kind.VALIDATION
    assert caught.value.code == "missing_coordinate"


def test_an_unsupported_storage_backend_is_refused_by_name() -> None:
    with pytest.raises(DomainError) as caught:
        wire.Campaign(config.Config(config.Spec(storage="postgres")), FakeTargetPolicyAllowing())

    assert caught.value.kind is Kind.VALIDATION
    assert caught.value.code == "unknown_backend"
    assert "postgres" in caught.value.message


def test_a_component_serves_a_whole_campaign_round_trip() -> None:
    built = wire.Campaign(config.Config(config.Spec(storage="memory")), FakeTargetPolicyAllowing())

    created = built.client.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    built.client.add_link(
        client.AddLinkRequest(
            campaign_id=created.campaign_id, slug="promo", target_url="https://ok.example/x"
        )
    )

    assert (
        built.client.resolve(client.ResolveRequest(slug="promo")).target_url
        == "https://ok.example/x"
    )


def test_a_component_hands_the_policy_it_was_given_to_the_service() -> None:
    built = wire.Campaign(config.Config(config.Spec(storage="memory")), FakeTargetPolicyBlocking())
    created = built.client.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    with pytest.raises(DomainError) as caught:
        built.client.add_link(
            client.AddLinkRequest(
                campaign_id=created.campaign_id, slug="promo", target_url="https://bad.example/x"
            )
        )

    assert caught.value.code == "destination_blocked"


def test_two_components_do_not_share_a_store() -> None:
    first = wire.Campaign(config.Config(config.Spec(storage="memory")), FakeTargetPolicyAllowing())
    second = wire.Campaign(config.Config(config.Spec(storage="memory")), FakeTargetPolicyAllowing())
    created = first.client.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    with pytest.raises(DomainError) as caught:
        second.client.get_campaign(client.GetCampaignRequest(campaign_id=created.campaign_id))

    assert caught.value.code == "campaign_missing"


def test_a_component_closes_what_it_built() -> None:
    built = wire.Campaign(config.Config(config.Spec(storage="memory")), FakeTargetPolicyAllowing())

    built.close()

    with pytest.raises(DomainError):
        built.client.get_campaign(client.GetCampaignRequest(campaign_id="0123456789abcdef"))
