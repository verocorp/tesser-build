from __future__ import annotations

import campaign
from bootstrap.bootstrap import new
from bootstrap.config import Config
from campaign.adapters.handlers.cli import Handler
from campaign.wiring.config import Config as CampaignConfig
from campaign.wiring.wire import build as build_campaign
from cliwire import CliRequest, CliResponse, UsageError, respond
from errors import InfraError, conflict, invalid, not_found
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from reports.wiring.config import Config as ReportsConfig
from srv.cli.main import commands_for, dispatch


class _AllowAllChecker:
    def check(self, target_url: str) -> campaign.CheckOutcome:
        return campaign.CheckOutcome(True, "ok")


def _handler() -> Handler:
    client, _ = build_campaign(CampaignConfig("memory"), _AllowAllChecker())
    return Handler(client)


def test_create_campaign_transforms_args_to_a_success_line() -> None:
    resp = _handler().create_campaign(CliRequest(("100.00", "USD")))
    assert resp.exit_code == 0
    assert resp.stdout.startswith("created campaign ")
    assert "budget 100.00 USD" in resp.stdout
    assert resp.stderr == ""


def test_a_domain_rejection_becomes_an_exit_code_not_a_traceback() -> None:
    resp = _handler().create_campaign(CliRequest(("-5", "USD")))
    assert resp.exit_code == 2
    assert resp.stdout == ""
    assert resp.stderr.startswith("[")


def test_a_missing_argument_is_a_usage_error() -> None:
    resp = _handler().create_campaign(CliRequest(("100.00",)))
    assert resp.exit_code == 2
    assert "usage: create-campaign" in resp.stderr


def test_extra_arguments_are_a_usage_error() -> None:
    resp = _handler().create_campaign(CliRequest(("100.00", "USD", "surplus")))
    assert resp.exit_code == 2
    assert "usage: create-campaign" in resp.stderr


def test_respond_maps_each_failure_class_to_an_exit_code() -> None:
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


def test_respond_never_leaks_internals_on_the_unexpected_path() -> None:
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
        return CliResponse(0, stdout="ok")

    resp = dispatch({"do-thing": _endpoint}, ["do-thing", "a", "b"])
    assert resp.exit_code == 0
    assert called == [CliRequest(("a", "b"))]


def test_dispatch_rejects_an_unknown_command_with_usage() -> None:
    resp = dispatch({"do-thing": lambda req: CliResponse(0)}, ["nope"])
    assert resp.exit_code == 2
    assert "usage:" in resp.stderr


def test_dispatch_rejects_no_command_with_usage() -> None:
    resp = dispatch({"do-thing": lambda req: CliResponse(0)}, [])
    assert resp.exit_code == 2
    assert "usage:" in resp.stderr


def test_commands_for_wires_the_campaign_commands_end_to_end() -> None:
    app = new(
        Config(
            campaign=CampaignConfig("memory"),
            linkpolicy=LinkPolicyConfig("memory"),
            reports=ReportsConfig(),
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
