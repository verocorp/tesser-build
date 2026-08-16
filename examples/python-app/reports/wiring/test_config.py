from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.client.client as campaign_client
import linkpolicy.client.client as linkpolicy_client
import reports.client.client as client
import reports.wiring.config as config
import reports.wiring.wire as wire


@ts.fake
class FakeCampaignClient(campaign_client.Client):
    def __init__(self, *links: campaign_client.LinkView) -> None:
        self.links = links

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


def test_the_context_takes_no_settings_yet() -> None:
    with pytest.raises(TypeError):
        config.Config("memory")  # type: ignore[call-arg]


def test_a_config_wires_a_client_that_serves_a_report() -> None:
    links = FakeCampaignClient(
        campaign_client.LinkView("spring-sale", "https://a.example/s", True)
    )
    verdicts = FakeLinkPolicyClient(
        linkpolicy_client.VerdictView("https://a.example/s", True, "on the allowlist")
    )

    component = wire.Reports(config.Config(), links, verdicts)
    try:
        resp = component.client.links_by_verdict(client.LinksByVerdictRequest())
        assert [view.slug for view in resp.links] == ["spring-sale"]
    finally:
        component.close()


def test_two_configs_wire_two_independent_clients() -> None:
    first = wire.Reports(
        config.Config(), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    second = wire.Reports(
        config.Config(), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    try:
        assert first.client is not second.client
    finally:
        first.close()
        second.close()


def test_a_config_carries_nothing_a_caller_must_set() -> None:
    component = wire.Reports(
        config.Config(), FakeCampaignClient(), FakeLinkPolicyClient()
    )
    try:
        assert component.client.links_by_verdict(client.LinksByVerdictRequest()).links == ()
    finally:
        component.close()
