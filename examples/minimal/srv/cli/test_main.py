from __future__ import annotations

import os

import pytest

import srv.cli as cli


class TestCliHost:

    def test_add_runs_the_add_command(self) -> None:
        os.environ.update(BETA_KEY="a")
        exit_code = cli.CliHost().run(["add", "a", "p"])
        assert exit_code == 0

    def test_a_missing_argument_or_command_exits_two_with_the_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        os.environ.update(BETA_KEY="a")
        exit_codes = [cli.CliHost().run(["add", "a"]), cli.CliHost().run(["a", "p"])]
        printed = capsys.readouterr().out
        assert exit_codes == [2, 2]
        assert "usage: add <name> <part>" in printed
        assert "usage: add <name> <part> | create <name> | approve <name> | find <name>" in printed

    def test_an_unexpected_failure_exits_one_and_leaks_nothing_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        ambient_storage = os.environ.get("ALPHA_STORAGE", "")
        os.environ.update(ALPHA_STORAGE="bogus", BETA_KEY="a")
        try:
            exit_code = cli.CliHost().run(["add", "a", "p"])
        finally:
            os.environ.update(ALPHA_STORAGE=ambient_storage)
        captured = capsys.readouterr()
        assert exit_code == 1
        assert captured.out == "unexpected error\n"
        assert "unknown_backend" in captured.err
