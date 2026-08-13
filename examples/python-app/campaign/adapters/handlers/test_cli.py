from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.adapters.handlers.cli as cli
import campaign.client.client as campaign_client
from errors import DomainError, invalid
from protocol.cli import CliRequest, UsageError


@ts.fake
class FakeCampaignClientScripted(campaign_client.Client):
    def __init__(
        self, *views: campaign_client.CampaignView, error: Exception | None = None
    ) -> None:
        self.pending = list(views)
        self.error = error
        self.requests: list[object] = []

    def _next(self, request: object) -> campaign_client.CampaignView:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def create_campaign(
        self, req: campaign_client.CreateCampaignRequest
    ) -> campaign_client.CampaignView:
        return self._next(req)

    def add_link(self, req: campaign_client.AddLinkRequest) -> campaign_client.CampaignView:
        return self._next(req)

    def deactivate_link(
        self, req: campaign_client.DeactivateLinkRequest
    ) -> campaign_client.CampaignView:
        return self._next(req)

    def get_campaign(
        self, req: campaign_client.GetCampaignRequest
    ) -> campaign_client.CampaignView:
        return self._next(req)

    def resolve(self, req: campaign_client.ResolveRequest) -> campaign_client.ResolveResponse:
        raise AssertionError("resolve is not part of the CLI surface")

    def list_links(
        self, req: campaign_client.ListLinksRequest
    ) -> campaign_client.ListLinksResponse:
        raise AssertionError("list_links is not part of the CLI surface")


def test_create_campaign_transforms_args_to_a_success_line() -> None:
    client = FakeCampaignClientScripted(
        campaign_client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    resp = cli.Handler(client).create_campaign(CliRequest(("100.00", "USD")))
    assert resp.exit_code == 0
    assert resp.stdout.startswith("created campaign ")
    assert "budget 100.00 USD" in resp.stdout
    assert resp.stderr == ""
    request = client.requests[0]
    assert isinstance(request, campaign_client.CreateCampaignRequest)
    assert request.budget_amount == "100.00"
    assert request.budget_currency == "USD"


def test_a_missing_argument_raises_a_usage_error() -> None:
    client = FakeCampaignClientScripted()
    with pytest.raises(UsageError):
        cli.Handler(client).create_campaign(CliRequest(("100.00",)))
    assert client.requests == []


def test_a_client_failure_propagates_out_of_the_handler() -> None:
    client = FakeCampaignClientScripted(error=invalid("bad_amount", "must be positive"))
    with pytest.raises(DomainError):
        cli.Handler(client).create_campaign(CliRequest(("-5", "USD")))
    assert len(client.requests) == 1
