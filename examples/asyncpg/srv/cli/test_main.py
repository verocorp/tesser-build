from __future__ import annotations

import srv.cli.main as main


class TestCliHost:

    def test_the_host_runs_the_command(self) -> None:
        exit_code = main.CliHost().run(["a", "p"])
        assert exit_code == 0
