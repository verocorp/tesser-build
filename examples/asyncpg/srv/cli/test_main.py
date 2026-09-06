from __future__ import annotations

import asyncio
import os

import pgdatabase.database as pgdatabase
import srv.cli as cli
import tesser.errors as errors


class TestCliHost:

    def test_the_host_runs_the_command(self) -> None:
        async def drop() -> None:  # tesser:debt TB023
            database = pgdatabase.Database(pgdatabase.DatabaseRequest(os.environ["ALPHA_STORAGE"]))
            await database.open()
            async with database.acquire() as connection:
                await connection.execute("DROP TABLE IF EXISTS widgets")
            await database.close()

        asyncio.run(drop())
        exit_code = cli.CliHost().run(["srv-cli", "p"])
        assert exit_code == 0

    def test_the_host_reports_the_conflict_of_a_second_add(self) -> None:
        async def drop() -> None:  # tesser:debt TB023
            database = pgdatabase.Database(pgdatabase.DatabaseRequest(os.environ["ALPHA_STORAGE"]))
            await database.open()
            async with database.acquire() as connection:
                await connection.execute("DROP TABLE IF EXISTS widgets")
            await database.close()

        asyncio.run(drop())
        assert cli.CliHost().run(["srv-cli-twice", "p"]) == 0
        assert cli.CliHost().run(["srv-cli-twice", "p"]) == errors.exit_code_for(
            errors.Kind.CONFLICT
        )
