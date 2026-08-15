from __future__ import annotations

from bootstrap.bootstrap import App, new
from bootstrap.config import from_env
from protocol.cli import CliRequest, CliResponse, UsageError
from tesser.errors import InfraError, conflict, invalid, not_found
from srv.cli.main import commands_for, dispatch, respond


def _app() -> App:  # tessercheck:ignore TB071
    env = {"CAMPAIGN_STORAGE": "memory", "LINKPOLICY_STORAGE": "memory"}
    return new(from_env(env.get))


def test_a_domain_rejection_becomes_an_exit_code_not_a_traceback() -> None:
    app = _app()
    try:
        resp = dispatch(commands_for(app), ["create-campaign", "-5", "USD"])
        assert resp.exit_code == 2
        assert resp.stdout == ""
        assert resp.stderr.startswith("[")
    finally:
        app.close()


def test_a_missing_argument_is_a_usage_error() -> None:
    app = _app()
    try:
        resp = dispatch(commands_for(app), ["create-campaign", "100.00"])
        assert resp.exit_code == 2
        assert "usage: create-campaign" in resp.stderr
    finally:
        app.close()


def test_an_empty_argument_is_a_usage_error() -> None:
    app = _app()
    try:
        resp = dispatch(commands_for(app), ["create-campaign", "", "USD"])
        assert resp.exit_code == 2
        assert "missing argument <budget_amount>" in resp.stderr
    finally:
        app.close()


def test_extra_arguments_are_a_usage_error() -> None:
    app = _app()
    try:
        resp = dispatch(commands_for(app), ["create-campaign", "100.00", "USD", "surplus"])
        assert resp.exit_code == 2
        assert "usage: create-campaign" in resp.stderr
    finally:
        app.close()


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
    app = _app()
    try:
        commands = commands_for(app)
        assert set(commands) == {"create-campaign", "add-link", "deactivate-link"}
        resp = commands["create-campaign"](CliRequest(("100.00", "USD")))
        assert resp.exit_code == 0
        assert resp.stdout.startswith("created campaign ")
    finally:
        app.close()
