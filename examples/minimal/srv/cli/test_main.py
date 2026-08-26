from __future__ import annotations

import os

import srv.cli.main as main


class TestCliHost:

    def test_the_host_runs_the_command(self) -> None:
        os.environ.update(ALPHA_STORAGE="memory", BETA_KEY="a")
        exit_code = main.CliHost().run(["a", "p"])
        assert exit_code == 0
