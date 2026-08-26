from __future__ import annotations

import os

import srv.cli.main as main


def test_the_host_runs_the_command_and_maps_usage_to_an_exit_code() -> None:
    os.environ["ALPHA_STORAGE"] = "memory"
    os.environ["BETA_KEY"] = "a"
    assert main.CliHost().run(["a"]) == 0
    assert main.CliHost().run([]) == 2
