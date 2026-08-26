from __future__ import annotations

import os

import srv.cli.main as main


def test_the_host_runs_the_command() -> None:
    os.environ.update(ALPHA_STORAGE="memory", BETA_KEY="a")
    assert main.CliHost().run(["a"]) == 0
