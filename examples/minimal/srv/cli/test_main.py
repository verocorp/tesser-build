from __future__ import annotations

import os

import pytest

import srv.cli as cli


class TestCliHost:

    def test_the_host_runs_the_command(self) -> None:
        os.environ.update(ALPHA_STORAGE="memory", BETA_KEY="a")
        exit_code = cli.CliHost().run(["a", "p"])
        assert exit_code == 0

    def test_a_missing_argument_exits_two_with_the_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        os.environ.update(ALPHA_STORAGE="memory", BETA_KEY="a")
        exit_code = cli.CliHost().run(["a"])
        assert exit_code == 2
        assert "usage: add <name> <part>" in capsys.readouterr().out

    def test_an_unexpected_failure_exits_one_and_leaks_nothing_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        os.environ.update(ALPHA_STORAGE="bogus", BETA_KEY="a")
        exit_code = cli.CliHost().run(["a", "p"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert captured.out == "unexpected error\n"
        assert "unknown_backend" in captured.err
