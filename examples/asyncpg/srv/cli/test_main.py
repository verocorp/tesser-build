from __future__ import annotations

import srv.cli.main as main
import tesser.errors as errors


class TestCliHost:

    def test_the_host_runs_the_command(self) -> None:
        exit_code = main.CliHost().run(["srv-cli", "p"])
        assert exit_code == 0

    def test_the_host_reports_the_conflict_of_a_second_add(self) -> None:
        assert main.CliHost().run(["srv-cli-twice", "p"]) == 0
        assert main.CliHost().run(["srv-cli-twice", "p"]) == errors.exit_code_for(
            errors.Kind.CONFLICT
        )
