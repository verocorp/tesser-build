from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application.ports as ports
import campaign.client as client
import campaign.component as component
import tesser.errors as errors


@ts.fake
class FakeTargetPolicyAllowing(ports.TargetPolicy):

    def check_target(
        self, check_target_request: ports.CheckTargetRequest
    ) -> ports.CheckTargetResponse:
        return ports.CheckTargetResponse(outcome=ports.CheckTargetOutcome.ALLOWED, reason="clean")


@ts.fake
class FakeTargetPolicyBlocking(ports.TargetPolicy):

    def check_target(
        self, check_target_request: ports.CheckTargetRequest
    ) -> ports.CheckTargetResponse:
        return ports.CheckTargetResponse(
            outcome=ports.CheckTargetOutcome.BLOCKED, reason="on the deny-list"
        )


def test_the_config_carries_the_storage_coordinate_it_was_given() -> None:
    config = component.Config(component.Spec(storage="memory"))

    assert config.storage == "memory"


def test_the_config_carries_an_unknown_coordinate_without_judging_it() -> None:
    config = component.Config(component.Spec(storage="postgres"))

    assert config.storage == "postgres"


def test_the_config_carries_an_absent_coordinate_without_judging_it() -> None:
    config = component.Config(component.Spec(storage=""))

    assert config.storage == ""


def test_two_configs_built_from_the_same_coordinate_are_separate_objects() -> None:
    first = component.Config(component.Spec(storage="memory"))
    second = component.Config(component.Spec(storage="memory"))

    assert first is not second
    assert first.storage == second.storage


def test_an_absent_storage_coordinate_is_refused_by_name() -> None:
    with pytest.raises(errors.DomainError) as caught:
        component.Campaign(
            component.Config(component.Spec(storage="")), FakeTargetPolicyAllowing()
        )

    assert caught.value.kind is errors.Kind.VALIDATION
    assert caught.value.code == "missing_coordinate"


def test_an_unsupported_storage_backend_is_refused_by_name() -> None:
    with pytest.raises(errors.DomainError) as caught:
        component.Campaign(
            component.Config(component.Spec(storage="postgres")), FakeTargetPolicyAllowing()
        )

    assert caught.value.kind is errors.Kind.VALIDATION
    assert caught.value.code == "unknown_backend"
    assert "postgres" in caught.value.message


def test_a_component_serves_a_whole_campaign_round_trip() -> None:
    campaign = component.Campaign(
        component.Config(component.Spec(storage="memory")), FakeTargetPolicyAllowing()
    )

    create_campaign_response = campaign.client.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )
    campaign.client.add_link(
        client.AddLinkRequest(
            campaign_id=create_campaign_response.campaign.campaign_id,
            slug="promo",
            target_url="https://ok.example/x",
        )
    )

    assert (
        campaign.client.resolve_slug(client.ResolveSlugRequest(slug="promo")).target_url
        == "https://ok.example/x"
    )


def test_a_component_hands_the_policy_it_was_given_to_the_service() -> None:
    campaign = component.Campaign(
        component.Config(component.Spec(storage="memory")), FakeTargetPolicyBlocking()
    )
    create_campaign_response = campaign.client.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    with pytest.raises(client.TargetBlocked) as caught:
        campaign.client.add_link(
            client.AddLinkRequest(
                campaign_id=create_campaign_response.campaign.campaign_id,
                slug="promo",
                target_url="https://bad.example/x",
            )
        )

    assert caught.value.message.startswith("destination not allowed: ")


def test_two_components_do_not_share_a_store() -> None:
    first = component.Campaign(
        component.Config(component.Spec(storage="memory")), FakeTargetPolicyAllowing()
    )
    second = component.Campaign(
        component.Config(component.Spec(storage="memory")), FakeTargetPolicyAllowing()
    )
    create_campaign_response = first.client.create_campaign(
        client.CreateCampaignRequest(budget_amount="100.00", budget_currency="USD")
    )

    with pytest.raises(client.CampaignNotFound) as caught:
        second.client.get_campaign(
            client.GetCampaignRequest(campaign_id=create_campaign_response.campaign.campaign_id)
        )

    assert caught.value.message == (
        f"no campaign with id {create_campaign_response.campaign.campaign_id!r}"
    )


def test_a_component_closes_what_it_built() -> None:
    campaign = component.Campaign(
        component.Config(component.Spec(storage="memory")), FakeTargetPolicyAllowing()
    )

    campaign.close()

    with pytest.raises(client.CampaignNotFound):
        campaign.client.get_campaign(client.GetCampaignRequest(campaign_id="0123456789abcdef"))
