from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.client as campaign_client
import linkpolicy.client as linkpolicy_client
import reports.client as client
import reports.component as component
import tesser.errors as errors


@ts.fake
class FakeCampaignClient(campaign_client.CampaignClient):
    def __init__(
        self, *links: campaign_client.LinkView, error: Exception | None = None
    ) -> None:
        self.links = links
        self.error = error

    def create_campaign(
        self, create_campaign_request: campaign_client.CreateCampaignRequest
    ) -> campaign_client.CampaignView:
        raise AssertionError("create_campaign is not part of the reports surface")

    def add_link(
        self, add_link_request: campaign_client.AddLinkRequest
    ) -> campaign_client.CampaignView:
        raise AssertionError("add_link is not part of the reports surface")

    def deactivate_link(
        self, deactivate_link_request: campaign_client.DeactivateLinkRequest
    ) -> campaign_client.CampaignView:
        raise AssertionError("deactivate_link is not part of the reports surface")

    def get_campaign(
        self, get_campaign_request: campaign_client.GetCampaignRequest
    ) -> campaign_client.CampaignView:
        raise AssertionError("get_campaign is not part of the reports surface")

    def resolve(
        self, resolve_request: campaign_client.ResolveRequest
    ) -> campaign_client.ResolveResponse:
        raise AssertionError("resolve is not part of the reports surface")

    def list_links(
        self, list_links_request: campaign_client.ListLinksRequest
    ) -> campaign_client.ListLinksResponse:
        if self.error is not None:
            raise self.error
        return campaign_client.ListLinksResponse(links=self.links)


@ts.fake
class FakeLinkPolicyClient(linkpolicy_client.LinkPolicyClient):
    def __init__(self, *verdicts: linkpolicy_client.VerdictView) -> None:
        self.verdicts = verdicts

    def check(
        self, check_request: linkpolicy_client.CheckRequest
    ) -> linkpolicy_client.CheckResponse:
        raise AssertionError("check is not part of the reports surface")

    def list_verdicts(
        self, list_verdicts_request: linkpolicy_client.ListVerdictsRequest
    ) -> linkpolicy_client.ListVerdictsResponse:
        return linkpolicy_client.ListVerdictsResponse(verdicts=self.verdicts)


def test_the_context_takes_no_settings_yet() -> None:
    with pytest.raises(TypeError):
        component.Config(component.Spec("memory"))  # type: ignore[call-arg]


def test_the_wired_client_joins_a_link_to_the_verdict_recorded_for_it() -> None:
    fake_campaign_client = FakeCampaignClient(
        campaign_client.LinkView("spring-sale", "https://a.example/s", "active")
    )
    fake_link_policy_client = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "denied", "host blocked")
    )

    reports = component.Reports(
        component.Config(component.Spec()), fake_campaign_client, fake_link_policy_client
    )
    try:
        links_by_verdict_response = reports.client.links_by_verdict(
            client.LinksByVerdictRequest()
        )
        assert [
            (view.slug, view.decision, view.reason)
            for view in links_by_verdict_response.links
        ] == [("spring-sale", "denied", "host blocked")]
    finally:
        reports.close()


def test_the_wired_client_reports_a_link_no_policy_has_ruled_on() -> None:
    fake_campaign_client = FakeCampaignClient(
        campaign_client.LinkView("spring-sale", "https://a.example/s", "active")
    )
    fake_link_policy_client = FakeLinkPolicyClient()

    reports = component.Reports(
        component.Config(component.Spec()), fake_campaign_client, fake_link_policy_client
    )
    try:
        links_by_verdict_response = reports.client.links_by_verdict(
            client.LinksByVerdictRequest()
        )
        assert [
            (view.slug, view.decision, view.reason)
            for view in links_by_verdict_response.links
        ] == [("spring-sale", "allowed", "no verdict recorded")]
    finally:
        reports.close()


def test_a_config_wires_a_client_that_serves_a_report() -> None:
    fake_campaign_client = FakeCampaignClient(
        campaign_client.LinkView("spring-sale", "https://a.example/s", "active")
    )
    fake_link_policy_client = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", "allowed", "on the allowlist")
    )

    reports = component.Reports(
        component.Config(component.Spec()), fake_campaign_client, fake_link_policy_client
    )
    try:
        links_by_verdict_response = reports.client.links_by_verdict(
            client.LinksByVerdictRequest()
        )
        assert [view.slug for view in links_by_verdict_response.links] == ["spring-sale"]
    finally:
        reports.close()


def test_the_wired_client_reports_nothing_when_neither_context_has_anything() -> None:
    reports = component.Reports(
        component.Config(component.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    try:
        assert reports.client.links_by_verdict(
            client.LinksByVerdictRequest()
        ).links == ()
    finally:
        reports.close()


def test_a_config_carries_nothing_a_caller_must_set() -> None:
    reports = component.Reports(
        component.Config(component.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    try:
        assert reports.client.links_by_verdict(
            client.LinksByVerdictRequest()
        ).links == ()
    finally:
        reports.close()


def test_closing_the_wired_graph_is_safe_to_repeat() -> None:
    reports = component.Reports(
        component.Config(component.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )

    reports.close()
    reports.close()

    assert reports.client.links_by_verdict(client.LinksByVerdictRequest()).links == ()


def test_two_builds_hand_back_two_independent_clients() -> None:
    first = component.Reports(
        component.Config(component.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    second = component.Reports(
        component.Config(component.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    try:
        assert first.client is not second.client
    finally:
        first.close()
        second.close()


def test_two_configs_wire_two_independent_clients() -> None:
    first = component.Reports(
        component.Config(component.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    second = component.Reports(
        component.Config(component.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    try:
        assert first.client is not second.client
    finally:
        first.close()
        second.close()


def test_a_failure_in_a_wired_neighbour_reaches_the_caller() -> None:
    fake_campaign_client = FakeCampaignClient(
        error=errors.InfraError("campaign store unreachable")
    )

    reports = component.Reports(
        component.Config(component.Spec()), fake_campaign_client, FakeLinkPolicyClient()
    )
    try:
        with pytest.raises(errors.InfraError):
            reports.client.links_by_verdict(client.LinksByVerdictRequest())
    finally:
        reports.close()
