from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.client.client as campaign_client
import linkpolicy.client.client as linkpolicy_client
import reports.client.client as client
import reports.component.config as config
import reports.component.component as wire
from tesser.errors import InfraError


@ts.fake
class FakeCampaignClient(campaign_client.Client):
    def __init__(
        self, *links: campaign_client.LinkView, error: Exception | None = None
    ) -> None:
        self.links = links
        self.error = error

    def create_campaign(
        self, req: campaign_client.CreateCampaignRequest
    ) -> campaign_client.CampaignView:
        raise AssertionError("create_campaign is not part of the reports surface")

    def add_link(self, req: campaign_client.AddLinkRequest) -> campaign_client.CampaignView:
        raise AssertionError("add_link is not part of the reports surface")

    def deactivate_link(
        self, req: campaign_client.DeactivateLinkRequest
    ) -> campaign_client.CampaignView:
        raise AssertionError("deactivate_link is not part of the reports surface")

    def get_campaign(
        self, req: campaign_client.GetCampaignRequest
    ) -> campaign_client.CampaignView:
        raise AssertionError("get_campaign is not part of the reports surface")

    def resolve(self, req: campaign_client.ResolveRequest) -> campaign_client.ResolveResponse:
        raise AssertionError("resolve is not part of the reports surface")

    def list_links(
        self, req: campaign_client.ListLinksRequest
    ) -> campaign_client.ListLinksResponse:
        if self.error is not None:
            raise self.error
        return campaign_client.ListLinksResponse(links=self.links)


@ts.fake
class FakeLinkPolicyClient(linkpolicy_client.Client):
    def __init__(self, *verdicts: linkpolicy_client.VerdictView) -> None:
        self.verdicts = verdicts

    def check(self, req: linkpolicy_client.CheckRequest) -> linkpolicy_client.CheckResponse:
        raise AssertionError("check is not part of the reports surface")

    def list_verdicts(
        self, req: linkpolicy_client.ListVerdictsRequest
    ) -> linkpolicy_client.ListVerdictsResponse:
        return linkpolicy_client.ListVerdictsResponse(verdicts=self.verdicts)


def test_the_wired_client_joins_a_link_to_the_verdict_recorded_for_it() -> None:
    links = FakeCampaignClient(
        campaign_client.LinkView("spring-sale", "https://a.example/s", True)
    )
    verdicts = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", False, "host blocked")
    )

    component = wire.Reports(config.Config(config.Spec()), links, verdicts)
    try:
        resp = component.client.links_by_verdict(client.LinksByVerdictRequest())
        assert [(view.slug, view.allowed, view.reason) for view in resp.links] == [
            ("spring-sale", False, "host blocked")
        ]
    finally:
        component.close()


def test_the_wired_client_reports_a_link_no_policy_has_ruled_on() -> None:
    links = FakeCampaignClient(
        campaign_client.LinkView("spring-sale", "https://a.example/s", True)
    )
    verdicts = FakeLinkPolicyClient()

    component = wire.Reports(config.Config(config.Spec()), links, verdicts)
    try:
        resp = component.client.links_by_verdict(client.LinksByVerdictRequest())
        assert [(view.slug, view.allowed, view.reason) for view in resp.links] == [
            ("spring-sale", True, "no verdict recorded")
        ]
    finally:
        component.close()


def test_the_wired_client_reports_nothing_when_neither_context_has_anything() -> None:
    component = wire.Reports(
        config.Config(config.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    try:
        assert component.client.links_by_verdict(client.LinksByVerdictRequest()).links == ()
    finally:
        component.close()


def test_closing_the_wired_graph_is_safe_to_repeat() -> None:
    component = wire.Reports(
        config.Config(config.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )

    component.close()
    component.close()

    assert component.client.links_by_verdict(client.LinksByVerdictRequest()).links == ()


def test_two_builds_hand_back_two_independent_clients() -> None:
    first = wire.Reports(
        config.Config(config.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    second = wire.Reports(
        config.Config(config.Spec()), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    try:
        assert first.client is not second.client
    finally:
        first.close()
        second.close()


def test_a_failure_in_a_wired_neighbour_reaches_the_caller() -> None:
    links = FakeCampaignClient(error=InfraError("campaign store unreachable"))

    component = wire.Reports(config.Config(config.Spec()), links, FakeLinkPolicyClient())
    try:
        with pytest.raises(InfraError):
            component.client.links_by_verdict(client.LinksByVerdictRequest())
    finally:
        component.close()
