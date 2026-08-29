from __future__ import annotations

import os

import asyncpg

import alpha.adapters.repositories.postgres as postgres
import alpha.application.ports.widget_repository as widget_repository
import pgdatabase.database as pgdatabase


class TestPostgresWidgetRepository:

    async def test_a_save_lands_the_name_in_the_widgets_table(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        widgets = postgres.PostgresWidgetRepository(database)
        saved = await widgets.save(widget_repository.SaveRequest(name="a"))
        await widgets.save(widget_repository.SaveRequest(name="a"))
        found = await widgets.find(widget_repository.FindRequest(name="a"))
        missing = await widgets.find(widget_repository.FindRequest(name="x"))
        await widgets.close()
        await database.close()
        rows = await connection.fetch("SELECT name FROM widgets")
        await connection.close()
        assert saved.name == "a"
        assert [row["name"] for row in rows] == ["a"]
        assert found.found is widget_repository.Found.YES
        assert missing.found is widget_repository.Found.NO

    async def test_close_releases_nothing_because_the_database_is_not_its_own(self) -> None:
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(os.environ["ALPHA_STORAGE"]))
        await database.open()
        widgets = postgres.PostgresWidgetRepository(database)
        await widgets.close()
        found = await widgets.find(widget_repository.FindRequest(name="x"))
        await database.close()
        assert found.found is widget_repository.Found.NO
