from __future__ import annotations

import os

import srv.cli.main as main


def test_a_missing_command_prints_usage() -> None:
    os.environ["ALPHA_STORAGE"] = "memory"
    os.environ["BETA_KEYS"] = "w"
    assert main.CliHost().run([]) == 2


def test_each_command_runs_through_the_host() -> None:
    os.environ["ALPHA_STORAGE"] = "memory"
    os.environ["BETA_KEYS"] = "w"
    assert main.CliHost().run(["add", "w", "a", "1"]) == 0
    assert main.CliHost().run(["get", "w"]) == 0
    assert main.CliHost().run(["get", "A1"]) == 2
    assert main.CliHost().run(["add", "w"]) == 2
