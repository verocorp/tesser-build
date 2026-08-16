from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.client.client as campaign_client
import reports.adapters.gateways.campaign_links as campaign_links
import reports.application.ports.link_source as link_source
from tesser.errors import InfraError


@ts.fake
class FakeCampaignClient(campaign_client.Client):
    def __init__(
        self, *links: campaign_client.LinkView, error: Exception | None = None
    ) -> None:
        self.links = links
        self.error = error
        self.requests: list[campaign_client.ListLinksRequest] = []

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
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        return campaign_client.ListLinksResponse(links=self.links)


def test_every_link_the_campaign_context_serves_becomes_a_link_record() -> None:
    links = FakeCampaignClient(
        campaign_client.LinkView("spring-sale", "https://a.example/s", True),
        campaign_client.LinkView("winter-sale", "https://a.example/w", False),
    )

    resp = campaign_links.CampaignLinkGateway(links).links(link_source.ListLinksRequest())

    assert [(record.slug, record.target_url) for record in resp.links] == [
        ("spring-sale", "https://a.example/s"),
        ("winter-sale", "https://a.example/w"),
    ]


def test_the_gateway_hands_back_records_and_never_the_foreign_view() -> None:
    links = FakeCampaignClient(
        campaign_client.LinkView("spring-sale", "https://a.example/s", True)
    )

    resp = campaign_links.CampaignLinkGateway(links).links(link_source.ListLinksRequest())

    assert isinstance(resp, link_source.ListLinksResponse)
    assert isinstance(resp.links[0], link_source.LinkRecord)


def test_the_gateway_asks_the_campaign_context_for_its_whole_link_list() -> None:
    links = FakeCampaignClient()

    campaign_links.CampaignLinkGateway(links).links(link_source.ListLinksRequest())

    assert len(links.requests) == 1
    assert isinstance(links.requests[0], campaign_client.ListLinksRequest)


def test_a_campaign_context_with_no_links_yields_no_records() -> None:
    links = FakeCampaignClient()

    resp = campaign_links.CampaignLinkGateway(links).links(link_source.ListLinksRequest())

    assert resp.links == ()


def test_a_failure_inside_the_campaign_context_reaches_the_caller() -> None:
    links = FakeCampaignClient(error=InfraError("campaign store unreachable"))

    with pytest.raises(InfraError):
        campaign_links.CampaignLinkGateway(links).links(link_source.ListLinksRequest())
