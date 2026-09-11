from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.client as client
import reports.adapters.gateways as gateways
import reports.application.ports as ports


@ts.fake
class FakeCampaignClient(client.CampaignClient):
    def __init__(
        self, *links: client.LinkView, error: Exception | None = None
    ) -> None:
        self.links = links
        self.error = error
        self.requests: list[client.ListLinksRequest] = []

    def create_campaign(
        self, create_campaign_request: client.CreateCampaignRequest
    ) -> client.CampaignView:
        raise AssertionError("create_campaign is not part of the reports surface")

    def add_link(self, add_link_request: client.AddLinkRequest) -> client.CampaignView:
        raise AssertionError("add_link is not part of the reports surface")

    def deactivate_link(
        self, deactivate_link_request: client.DeactivateLinkRequest
    ) -> client.CampaignView:
        raise AssertionError("deactivate_link is not part of the reports surface")

    def get_campaign(
        self, get_campaign_request: client.GetCampaignRequest
    ) -> client.CampaignView:
        raise AssertionError("get_campaign is not part of the reports surface")

    def resolve(self, resolve_request: client.ResolveRequest) -> client.ResolveResponse:
        raise AssertionError("resolve is not part of the reports surface")

    def list_links(
        self, list_links_request: client.ListLinksRequest
    ) -> client.ListLinksResponse:
        self.requests.append(list_links_request)
        if self.error is not None:
            raise self.error
        return client.ListLinksResponse(links=self.links)


def test_every_link_the_campaign_context_serves_becomes_a_link_record() -> None:
    fake_campaign_client = FakeCampaignClient(
        client.LinkView("spring-sale", "https://a.example/s", "active"),
        client.LinkView("winter-sale", "https://a.example/w", "inactive"),
    )

    list_links_response = gateways.CampaignLinkGateway(fake_campaign_client).links(ports.ListLinksRequest())

    assert [(record.slug, record.target_url) for record in list_links_response.links] == [
        ("spring-sale", "https://a.example/s"),
        ("winter-sale", "https://a.example/w"),
    ]


def test_the_gateway_hands_back_records_and_never_the_foreign_view() -> None:
    fake_campaign_client = FakeCampaignClient(
        client.LinkView("spring-sale", "https://a.example/s", "active")
    )

    list_links_response = gateways.CampaignLinkGateway(fake_campaign_client).links(ports.ListLinksRequest())

    assert isinstance(list_links_response, ports.ListLinksResponse)
    assert isinstance(list_links_response.links[0], ports.LinkRecord)


def test_the_gateway_asks_the_campaign_context_for_its_whole_link_list() -> None:
    fake_campaign_client = FakeCampaignClient()

    gateways.CampaignLinkGateway(fake_campaign_client).links(ports.ListLinksRequest())

    assert len(fake_campaign_client.requests) == 1
    assert isinstance(fake_campaign_client.requests[0], client.ListLinksRequest)


def test_a_campaign_context_with_no_links_yields_no_records() -> None:
    fake_campaign_client = FakeCampaignClient()

    list_links_response = gateways.CampaignLinkGateway(fake_campaign_client).links(ports.ListLinksRequest())

    assert list_links_response.links == ()


def test_a_campaign_context_that_cannot_answer_is_the_ports_unavailable() -> None:
    fake_campaign_client = FakeCampaignClient(
        error=client.Unavailable("the campaign store is unavailable")
    )

    with pytest.raises(ports.LinkSourceUnavailable) as caught:
        gateways.CampaignLinkGateway(fake_campaign_client).links(ports.ListLinksRequest())
    assert isinstance(caught.value.__cause__, client.Unavailable)


def test_a_failure_the_campaign_context_never_declared_reaches_the_caller() -> None:
    fake_campaign_client = FakeCampaignClient(error=RuntimeError("campaign store unreachable"))

    with pytest.raises(RuntimeError):
        gateways.CampaignLinkGateway(fake_campaign_client).links(ports.ListLinksRequest())
