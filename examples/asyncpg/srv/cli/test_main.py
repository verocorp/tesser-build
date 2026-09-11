from __future__ import annotations

import asyncio
import os

import asyncpg

import srv.cli as cli


class TestCliHost:

    def test_the_host_runs_the_command(self) -> None:
        with asyncio.Runner() as runner:
            connection = runner.run(asyncpg.connect(os.environ["ALPHA_STORAGE"]))
            runner.run(connection.execute("DROP TABLE IF EXISTS widgets"))
            runner.run(connection.close())

        exit_code = cli.CliHost().run(["srv-cli", "p"])

        assert exit_code == 0

    def test_the_host_reports_the_conflict_of_a_second_add(self) -> None:
        with asyncio.Runner() as runner:
            connection = runner.run(asyncpg.connect(os.environ["ALPHA_STORAGE"]))
            runner.run(connection.execute("DROP TABLE IF EXISTS widgets"))
            runner.run(connection.close())

        assert cli.CliHost().run(["srv-cli-twice", "p"]) == 0
        assert cli.CliHost().run(["srv-cli-twice", "p"]) == 1
