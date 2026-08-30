from __future__ import annotations

import asyncio
import os

import asyncpg
import pytest

import alpha.adapters.repositories.postgres as postgres
import alpha.application.ports.widget_repository as widget_repository
import pgdatabase.database as pgdatabase
import tesser.errors as errors


class TestPostgresWidgetStore:

    async def test_a_saved_widget_is_loaded_and_found_in_a_later_transaction(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        widget_store = postgres.PostgresWidgetStore(database)
        async with widget_store.transaction() as widgets_repo:
            saved = await widgets_repo.save_widget(widget_repository.SaveWidgetRequest(name="a", part="p", standing="kept"))
        async with widget_store.transaction() as widgets_repo:
            loaded = await widgets_repo.load_widget(widget_repository.LoadWidgetRequest(name="a"))
            found = await widgets_repo.find_widget(widget_repository.FindWidgetRequest(name="a"))
            missing = await widgets_repo.find_widget(widget_repository.FindWidgetRequest(name="x"))
        await database.close()
        assert saved.name == "a"
        assert loaded.part == "p"
        assert loaded.standing == "kept"
        assert found.found is widget_repository.Found.YES
        assert missing.found is widget_repository.Found.NO

    async def test_a_released_widget_is_loaded_back_as_released(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        widget_store = postgres.PostgresWidgetStore(database)
        async with widget_store.transaction() as widgets_repo:
            await widgets_repo.save_widget(
                widget_repository.SaveWidgetRequest(name="a", part="p", standing="released")
            )
        async with widget_store.transaction() as widgets_repo:
            loaded = await widgets_repo.load_widget(widget_repository.LoadWidgetRequest(name="a"))
        await database.close()
        assert loaded.standing == "released"

    async def test_loading_an_unknown_widget_is_not_found(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        widget_store = postgres.PostgresWidgetStore(database)
        with pytest.raises(errors.DomainError) as caught:
            async with widget_store.transaction() as widgets_repo:
                await widgets_repo.load_widget(widget_repository.LoadWidgetRequest(name="x"))
        await database.close()
        assert caught.value.kind is errors.Kind.NOT_FOUND

    async def test_a_transaction_that_raises_is_rolled_back(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        widget_store = postgres.PostgresWidgetStore(database)
        async with widget_store.transaction() as widgets_repo:
            await widgets_repo.save_widget(widget_repository.SaveWidgetRequest(name="a", part="p", standing="kept"))
        with pytest.raises(RuntimeError):
            async with widget_store.transaction() as widgets_repo:
                await widgets_repo.save_widget(widget_repository.SaveWidgetRequest(name="a", part="q", standing="kept"))
                raise RuntimeError("abort")
        async with widget_store.transaction() as widgets_repo:
            loaded = await widgets_repo.load_widget(widget_repository.LoadWidgetRequest(name="a"))
        await database.close()
        assert loaded.part == "p"

    async def test_the_schema_outlives_a_first_transaction_that_rolls_back(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        widget_store = postgres.PostgresWidgetStore(database)
        with pytest.raises(RuntimeError):
            async with widget_store.transaction() as widgets_repo:
                await widgets_repo.save_widget(widget_repository.SaveWidgetRequest(name="a", part="p"))
                raise RuntimeError("abort")
        await database.close()
        connection = await asyncpg.connect(dsn)
        table = await connection.fetchval("SELECT to_regclass('widgets') IS NOT NULL")
        await connection.close()
        assert table is True

    async def test_a_load_holds_the_row_until_the_transaction_ends(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn), min_size=1, max_size=2)
        await database.open()
        widget_store = postgres.PostgresWidgetStore(database)
        async with widget_store.transaction() as widgets_repo:
            await widgets_repo.save_widget(widget_repository.SaveWidgetRequest(name="a", part="p", standing="kept"))
        first_loaded = asyncio.Event()
        release_first = asyncio.Event()
        order: list[str] = []

        async def first() -> None:
            async with widget_store.transaction() as widgets_repo:
                await widgets_repo.load_widget(widget_repository.LoadWidgetRequest(name="a"))
                first_loaded.set()
                await release_first.wait()
                await widgets_repo.save_widget(widget_repository.SaveWidgetRequest(name="a", part="first", standing="kept"))
                order.append("first")

        async def second() -> None:
            await first_loaded.wait()
            async with widget_store.transaction() as widgets_repo:
                loaded = await widgets_repo.load_widget(widget_repository.LoadWidgetRequest(name="a"))
                order.append(f"second saw {loaded.part}")

        second_task = asyncio.create_task(second())
        first_task = asyncio.create_task(first())
        await first_loaded.wait()
        await asyncio.sleep(0.1)
        waited = list(order)
        release_first.set()
        await asyncio.gather(first_task, second_task)
        await database.close()
        assert waited == []
        assert order == ["first", "second saw first"]
