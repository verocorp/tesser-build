from __future__ import annotations

from pathlib import Path

import tessercheck.adapters.handlers.cli as cli
from bootstrap.loader import load
from protocol.cli import CliResponse, UsageError
from srv.cli.rules import dispatch, respond, settle


def test_a_usage_error_becomes_exit_code_two_with_the_usage_line() -> None:
    def raising() -> CliResponse:
        raise UsageError("unexpected extra arguments")

    resp = respond(raising)
    assert resp.exit_code == 2
    assert resp.stdout == ""
    assert "usage: python -m srv.cli.rules" in resp.stderr


def test_the_host_never_leaks_internals_on_the_unexpected_path() -> None:
    def raising() -> CliResponse:
        raise RuntimeError("secret stack detail")

    resp = respond(raising)
    assert resp.exit_code == 1
    assert "secret" not in resp.stderr
    assert resp.stderr == "unexpected error"


def test_an_extra_argument_dispatches_to_exit_code_two() -> None:
    app = load()
    try:
        resp = dispatch(cli.Handler(app.tessercheck.client), [".", "surplus"])
        assert resp.exit_code == 2
        assert resp.stdout == ""
    finally:
        app.close()


def test_a_tree_dispatches_to_a_rendered_rulebook_on_stdout() -> None:
    root = Path(__file__).resolve().parents[2]
    app = load()
    try:
        resp = dispatch(cli.Handler(app.tessercheck.client), [str(root)])
        assert resp.exit_code == 0
        assert resp.stdout.startswith("# Rules implemented in the spike")
        assert resp.stderr == ""
    finally:
        app.close()


def test_settling_without_check_writes_the_rendering(tmp_path: Path) -> None:
    output = tmp_path / "RULES.md"
    assert settle("| a row |\n", output, False) == 0
    assert output.read_text() == "| a row |\n"


def test_settling_without_check_replaces_a_stale_rendering(tmp_path: Path) -> None:
    output = tmp_path / "RULES.md"
    output.write_text("| an old row |\n")
    assert settle("| a new row |\n", output, False) == 0
    assert output.read_text() == "| a new row |\n"


def test_checking_a_matching_rendering_settles_at_zero(tmp_path: Path) -> None:
    output = tmp_path / "RULES.md"
    output.write_text("| a row |\n")
    assert settle("| a row |\n", output, True) == 0


def test_checking_a_stale_rendering_settles_at_one(tmp_path: Path) -> None:
    output = tmp_path / "RULES.md"
    output.write_text("| an old row |\n")
    assert settle("| a new row |\n", output, True) == 1
    assert output.read_text() == "| an old row |\n"


def test_checking_a_missing_rendering_settles_at_one(tmp_path: Path) -> None:
    output = tmp_path / "RULES.md"
    assert settle("| a row |\n", output, True) == 1
    assert not output.exists()
