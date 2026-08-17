from __future__ import annotations

from pathlib import Path

import tessercheck.adapters.handlers.cli as cli
from app.loader import load
from protocol.cli import CliResponse, UsageError
from srv.cli.main import dispatch, respond, run


def test_a_clean_tree_dispatches_to_exit_code_zero(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    app = load()
    try:
        resp = dispatch(cli.Handler(app.tessercheck.client), [str(tmp_path)])
        assert resp.exit_code == 0
        assert resp.stdout == ""
        assert resp.stderr == ""
    finally:
        app.close()


def test_a_finding_dispatches_to_exit_code_one(tmp_path: Path) -> None:
    app = load()
    try:
        resp = dispatch(cli.Handler(app.tessercheck.client), [str(tmp_path)])
        assert resp.exit_code == 1
        assert "TB044" in resp.stdout
    finally:
        app.close()


def test_the_app_closes_idempotently(tmp_path: Path) -> None:
    app = load()
    app.close()
    app.close()


def test_a_usage_error_becomes_exit_code_two_with_the_usage_line() -> None:
    def raising() -> CliResponse:
        raise UsageError("unexpected extra arguments")

    resp = respond(raising)
    assert resp.exit_code == 2
    assert resp.stdout == ""
    assert "usage: python -m srv.cli.main" in resp.stderr


def test_the_host_never_leaks_internals_on_the_unexpected_path() -> None:
    def raising() -> CliResponse:
        raise RuntimeError("secret stack detail")

    resp = respond(raising)
    assert resp.exit_code == 1
    assert "secret" not in resp.stderr
    assert resp.stderr == "unexpected error"


def test_run_builds_the_app_and_returns_the_exit_code(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    assert run([str(tmp_path)]) == 0


def test_run_returns_one_when_the_tree_is_undeclared(tmp_path: Path) -> None:
    assert run([str(tmp_path)]) == 1


def test_run_rejects_an_extra_argument_with_exit_code_two(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    assert run([str(tmp_path), "surplus"]) == 2
