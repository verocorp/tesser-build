from __future__ import annotations

import asyncio
import os

import asyncpg
import pytest

import alpha.adapters.repositories as repositories
import alpha.application.ports as ports
import pgdatabase.database as pgdatabase_database


class TestPostgresWidgetStore:

    async def test_a_saved_widget_is_loaded_and_found_in_a_later_transaction(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_widget_store = repositories.PostgresWidgetStore(database)
        async with postgres_widget_store.transaction() as widget_repository:
            saved = await widget_repository.save_widget(ports.SaveWidgetRequest(name="a", part="p", standing="kept"))
        async with postgres_widget_store.transaction() as widget_repository:
            loaded = await widget_repository.load_widget(ports.LoadWidgetRequest(name="a"))
            found = await widget_repository.find_widget(ports.FindWidgetRequest(name="a"))
            missing = await widget_repository.find_widget(ports.FindWidgetRequest(name="x"))
        await database.close()
        assert saved.name == "a"
        assert loaded.outcome is ports.LoadWidgetOutcome.FOUND
        assert loaded.widgets[0].part == "p"
        assert loaded.widgets[0].standing == "kept"
        assert found.outcome is ports.FindWidgetOutcome.YES
        assert missing.outcome is ports.FindWidgetOutcome.NO

    async def test_a_released_widget_is_loaded_back_as_released(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_widget_store = repositories.PostgresWidgetStore(database)
        async with postgres_widget_store.transaction() as widget_repository:
            await widget_repository.save_widget(
                ports.SaveWidgetRequest(name="a", part="p", standing="released")
            )
        async with postgres_widget_store.transaction() as widget_repository:
            loaded = await widget_repository.load_widget(ports.LoadWidgetRequest(name="a"))
        await database.close()
        assert loaded.widgets[0].standing == "released"

    async def test_adding_a_stored_name_answers_exists_and_leaves_the_row_alone(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_widget_store = repositories.PostgresWidgetStore(database)
        async with postgres_widget_store.transaction() as widget_repository:
            await widget_repository.add_widget(
                ports.AddWidgetRequest(name="a", part="p", standing="released")
            )
        async with postgres_widget_store.transaction() as widget_repository:
            again = await widget_repository.add_widget(
                ports.AddWidgetRequest(name="a", part="q", standing="kept")
            )
        async with postgres_widget_store.transaction() as widget_repository:
            loaded = await widget_repository.load_widget(ports.LoadWidgetRequest(name="a"))
        await database.close()
        assert again.outcome is ports.AddWidgetOutcome.EXISTS
        assert loaded.widgets[0].part == "p"
        assert loaded.widgets[0].standing == "released"

    async def test_the_schema_step_adds_the_standing_column_to_an_older_table(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.execute(
            "CREATE TABLE widgets (name text PRIMARY KEY, part text NOT NULL)"
        )
        await connection.execute("INSERT INTO widgets (name, part) VALUES ('old', 'p')")
        await connection.close()
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_widget_store = repositories.PostgresWidgetStore(database)
        async with postgres_widget_store.transaction() as widget_repository:
            loaded = await widget_repository.load_widget(ports.LoadWidgetRequest(name="old"))
        await database.close()
        assert loaded.widgets[0].standing == "kept"

    async def test_loading_an_unknown_widget_answers_missing(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_widget_store = repositories.PostgresWidgetStore(database)
        async with postgres_widget_store.transaction() as widget_repository:
            loaded = await widget_repository.load_widget(ports.LoadWidgetRequest(name="x"))
        await database.close()
        assert loaded.outcome is ports.LoadWidgetOutcome.NOT_FOUND
        assert loaded.widgets == ()

    async def test_a_transaction_that_raises_is_rolled_back(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_widget_store = repositories.PostgresWidgetStore(database)
        async with postgres_widget_store.transaction() as widget_repository:
            await widget_repository.save_widget(ports.SaveWidgetRequest(name="a", part="p", standing="kept"))
        with pytest.raises(RuntimeError):
            async with postgres_widget_store.transaction() as widget_repository:
                await widget_repository.save_widget(ports.SaveWidgetRequest(name="a", part="q", standing="kept"))
                raise RuntimeError("abort")
        async with postgres_widget_store.transaction() as widget_repository:
            loaded = await widget_repository.load_widget(ports.LoadWidgetRequest(name="a"))
        await database.close()
        assert loaded.widgets[0].part == "p"

    async def test_the_schema_outlives_a_first_transaction_that_rolls_back(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS widgets")
        await connection.close()
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_widget_store = repositories.PostgresWidgetStore(database)
        with pytest.raises(RuntimeError):
            async with postgres_widget_store.transaction() as widget_repository:
                await widget_repository.save_widget(ports.SaveWidgetRequest(name="a", part="p", standing="kept"))
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
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn), min_size=1, max_size=2)
        await database.open()
        postgres_widget_store = repositories.PostgresWidgetStore(database)
        async with postgres_widget_store.transaction() as widget_repository:
            await widget_repository.save_widget(ports.SaveWidgetRequest(name="a", part="p", standing="kept"))
        async with postgres_widget_store.transaction() as second_repository:
            async with postgres_widget_store.transaction() as first_repository:
                await first_repository.load_widget(ports.LoadWidgetRequest(name="a"))
                second_load = asyncio.create_task(second_repository.load_widget(ports.LoadWidgetRequest(name="a")))
                await asyncio.sleep(0.1)
                assert not second_load.done()
                await first_repository.save_widget(ports.SaveWidgetRequest(name="a", part="first", standing="kept"))
            loaded = await second_load
        await database.close()
        assert loaded.widgets[0].part == "first"
