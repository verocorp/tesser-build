from __future__ import annotations

import os

import asyncpg

import alpha.adapters.repositories.postgres as postgres
import alpha.application.ports.widget_repository as widget_repository


class TestPostgresWidgetRepository:

    async def test_a_save_lands_the_name_in_the_widgets_table(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        widgets = postgres.PostgresWidgetRepository(dsn)
        saved = await widgets.save(widget_repository.SaveRequest(name="a"))
        await widgets.save(widget_repository.SaveRequest(name="a"))
        await widgets.close()
        rows = await connection.fetch("SELECT name FROM widgets")
        await connection.close()
        assert saved.name == "a"
        assert [row["name"] for row in rows] == ["a"]

    async def test_close_before_any_save_releases_nothing(self) -> None:
        widgets = postgres.PostgresWidgetRepository(os.environ["ALPHA_STORAGE"])
        await widgets.close()
