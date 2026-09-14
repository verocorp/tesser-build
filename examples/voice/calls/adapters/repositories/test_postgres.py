from __future__ import annotations

import os

import asyncpg

import calls.adapters.repositories as repositories
import calls.application.ports as ports
import pgdatabase.database as pgdatabase_database


class TestPostgresCallStore:

    async def test_a_saved_call_is_loaded_in_a_later_transaction(self) -> None:
        dsn = os.environ["CALLS_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS calls")
        await connection.close()
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_call_store = repositories.PostgresCallStore(database)

        async with postgres_call_store.transaction() as call_repository:
            await call_repository.save_call(
                ports.SaveCallRequest(call_id="c1", person_name="Grace", phone_number="+15555550100")
            )
        async with postgres_call_store.transaction() as call_repository:
            load_call_response = await call_repository.load_call(ports.LoadCallRequest(call_id="c1"))
        await database.close()

        assert load_call_response.calls == (
            ports.Call(call_id="c1", person_name="Grace", phone_number="+15555550100"),
        )
