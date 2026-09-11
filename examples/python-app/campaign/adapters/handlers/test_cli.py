from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.adapters.handlers as handlers
import campaign.client as client
import protocol as protocol


@ts.fake
class FakeCampaignClientScripted(client.CampaignClient):
    def __init__(
        self, *views: client.CampaignView, error: Exception | None = None
    ) -> None:
        self.pending = list(views)
        self.error = error
        self.requests: list[object] = []

    def create_campaign(
        self, create_campaign_request: client.CreateCampaignRequest
    ) -> client.CampaignView:
        self.requests.append(create_campaign_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def add_link(self, add_link_request: client.AddLinkRequest) -> client.CampaignView:
        self.requests.append(add_link_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def deactivate_link(
        self, deactivate_link_request: client.DeactivateLinkRequest
    ) -> client.CampaignView:
        self.requests.append(deactivate_link_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def get_campaign(
        self, get_campaign_request: client.GetCampaignRequest
    ) -> client.CampaignView:
        self.requests.append(get_campaign_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def resolve(self, resolve_request: client.ResolveRequest) -> client.ResolveResponse:
        raise AssertionError("resolve is not part of the CLI surface")

    def list_links(
        self, list_links_request: client.ListLinksRequest
    ) -> client.ListLinksResponse:
        raise AssertionError("list_links is not part of the CLI surface")


def test_create_campaign_transforms_args_to_a_success_line() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted(
        client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    cli_response = handlers.CliHandler(fake_campaign_client_scripted).create_campaign(protocol.CliRequest(("100.00", "USD")))
    assert cli_response.exit_code == 0
    assert cli_response.stdout.startswith("created campaign ")
    assert "budget 100.00 USD" in cli_response.stdout
    assert cli_response.stderr == ""
    request = fake_campaign_client_scripted.requests[0]
    assert isinstance(request, client.CreateCampaignRequest)
    assert request.budget_amount == "100.00"
    assert request.budget_currency == "USD"


def test_a_missing_argument_raises_a_usage_error() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted()
    with pytest.raises(protocol.UsageError):
        handlers.CliHandler(fake_campaign_client_scripted).create_campaign(protocol.CliRequest(("100.00",)))
    assert fake_campaign_client_scripted.requests == []


def test_a_rejection_exits_two_and_names_the_contexts_code() -> None:
    cli_handler = handlers.CliHandler(FakeCampaignClientScripted(error=client.Rejected("bad_amount", "must be positive")))

    cli_response = cli_handler.create_campaign(protocol.CliRequest(("-5", "USD")))

    assert cli_response.exit_code == 2
    assert cli_response.stderr == "[bad_amount] must be positive"
    assert cli_response.stdout == ""


def test_a_missing_campaign_exits_one_and_names_the_contexts_code() -> None:
    cli_handler = handlers.CliHandler(FakeCampaignClientScripted(error=client.Missing("campaign_missing", "no campaign with id 'x'")))

    cli_response = cli_handler.create_campaign(protocol.CliRequest(("-5", "USD")))

    assert cli_response.exit_code == 1
    assert cli_response.stderr == "[campaign_missing] no campaign with id 'x'"


def test_a_conflict_exits_one_and_names_the_contexts_code() -> None:
    cli_handler = handlers.CliHandler(FakeCampaignClientScripted(error=client.Conflict("duplicate_slug", "slug 'promo' already exists")))

    cli_response = cli_handler.create_campaign(protocol.CliRequest(("-5", "USD")))

    assert cli_response.exit_code == 1
    assert cli_response.stderr == "[duplicate_slug] slug 'promo' already exists"


def test_an_unreadable_record_exits_one_and_leaks_nothing() -> None:
    cli_handler = handlers.CliHandler(FakeCampaignClientScripted(error=client.Unreadable("stored campaign 'x' cannot be read back")))

    cli_response = cli_handler.create_campaign(protocol.CliRequest(("-5", "USD")))

    assert cli_response.exit_code == 1
    assert cli_response.stderr == "a dependency is unavailable; please retry"


def test_a_failure_the_context_never_declared_leaves_the_handler() -> None:
    cli_handler = handlers.CliHandler(
        FakeCampaignClientScripted(error=RuntimeError("a stack trace nobody should see"))
    )

    with pytest.raises(RuntimeError):
        cli_handler.create_campaign(protocol.CliRequest(("-5", "USD")))
