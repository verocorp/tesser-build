from __future__ import annotations

import tesser.testing as ts

import campaign.client.client as campaign_client
from bootstrap.bootstrap import new
from bootstrap.config import Config
import campaign.adapters.handlers.cli as cli
import campaign.wiring.config as config
from protocol.cli import CliRequest, CliResponse, UsageError
from errors import InfraError, conflict, invalid, not_found
import linkpolicy.wiring.config as linkpolicy_config
import reports.wiring.config as reports_config
from srv.cli.main import commands_for, dispatch, respond


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


def test_a_domain_rejection_becomes_an_exit_code_not_a_traceback() -> None:
    client = FakeCampaignClientScripted(error=invalid("bad_amount", "must be positive"))
    resp = dispatch({"create-campaign": cli.Handler(client).create_campaign}, ["create-campaign", "-5", "USD"])
    assert resp.exit_code == 2
    assert resp.stdout == ""
    assert resp.stderr.startswith("[")


def test_a_missing_argument_is_a_usage_error() -> None:
    client = FakeCampaignClientScripted()
    resp = dispatch({"create-campaign": cli.Handler(client).create_campaign}, ["create-campaign", "100.00"])
    assert resp.exit_code == 2
    assert "usage: create-campaign" in resp.stderr


def test_an_empty_argument_is_a_usage_error() -> None:
    client = FakeCampaignClientScripted()
    resp = dispatch({"create-campaign": cli.Handler(client).create_campaign}, ["create-campaign", "", "USD"])
    assert resp.exit_code == 2
    assert "missing argument <budget_amount>" in resp.stderr


def test_extra_arguments_are_a_usage_error() -> None:
    client = FakeCampaignClientScripted()
    resp = dispatch({"create-campaign": cli.Handler(client).create_campaign}, ["create-campaign", "100.00", "USD", "surplus"])
    assert resp.exit_code == 2
    assert "usage: create-campaign" in resp.stderr


def test_the_host_maps_each_failure_class_to_an_exit_code() -> None:
    def raising(exc: Exception) -> CliResponse:
        def run() -> CliResponse:
            raise exc

        return respond(run)

    assert raising(UsageError("bad")).exit_code == 2
    assert raising(invalid("bad_amount", "must be positive")).exit_code == 2
    assert raising(not_found("no_campaign", "not found")).exit_code == 1
    assert raising(conflict("dup_slug", "already exists")).exit_code == 1
    assert raising(InfraError("down")).exit_code == 1
    assert raising(RuntimeError("boom")).exit_code == 1


def test_the_host_never_leaks_internals_on_the_unexpected_path() -> None:
    def run() -> CliResponse:
        raise RuntimeError("secret stack detail")

    resp = respond(run)
    assert resp.exit_code == 1
    assert "secret" not in resp.stderr
    assert resp.stderr == "unexpected error"


def test_dispatch_routes_a_known_command() -> None:
    called: list[CliRequest] = []

    def _endpoint(req: CliRequest) -> CliResponse:
        called.append(req)
        return CliResponse(0, stdout="ok", stderr="")

    resp = dispatch({"do-thing": _endpoint}, ["do-thing", "a", "b"])
    assert resp.exit_code == 0
    assert [req.args for req in called] == [("a", "b")]


def test_dispatch_rejects_an_unknown_command_with_usage() -> None:
    resp = dispatch({"do-thing": lambda req: CliResponse(0, "", "")}, ["nope"])
    assert resp.exit_code == 2
    assert "usage:" in resp.stderr


def test_dispatch_rejects_no_command_with_usage() -> None:
    resp = dispatch({"do-thing": lambda req: CliResponse(0, "", "")}, [])
    assert resp.exit_code == 2
    assert "usage:" in resp.stderr


def test_commands_for_wires_the_campaign_commands_end_to_end() -> None:
    app = new(
        Config(
            campaign=config.Config("memory"),
            linkpolicy=linkpolicy_config.Config("memory"),
            reports=reports_config.Config(),
        )
    )
    try:
        commands = commands_for(app)
        assert set(commands) == {"create-campaign", "add-link", "deactivate-link"}
        resp = commands["create-campaign"](CliRequest(("100.00", "USD")))
        assert resp.exit_code == 0
        assert resp.stdout.startswith("created campaign ")
    finally:
        app.close()
