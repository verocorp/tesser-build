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
            await call_repository.save_call(ports.SaveCallRequest(call_id="c1", person_name="Grace"))
        async with postgres_call_store.transaction() as call_repository:
            load_call_response = await call_repository.load_call(ports.LoadCallRequest(call_id="c1"))
        await database.close()

        assert load_call_response.calls == (ports.Call(call_id="c1", person_name="Grace"),)

    async def test_a_call_that_was_never_saved_is_not_found(self) -> None:
        dsn = os.environ["CALLS_STORAGE"]
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_call_store = repositories.PostgresCallStore(database)

        async with postgres_call_store.transaction() as call_repository:
            load_call_response = await call_repository.load_call(ports.LoadCallRequest(call_id="never-saved"))
        await database.close()

        assert load_call_response.outcome is ports.LoadCallOutcome.NOT_FOUND

    async def test_saving_a_call_a_second_time_is_a_retry_not_a_conflict(self) -> None:
        dsn = os.environ["CALLS_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS calls")
        await connection.close()
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_call_store = repositories.PostgresCallStore(database)

        for _ in (1, 2):
            async with postgres_call_store.transaction() as call_repository:
                await call_repository.save_call(ports.SaveCallRequest(call_id="c1", person_name="Grace"))
        async with postgres_call_store.transaction() as call_repository:
            load_call_response = await call_repository.load_call(ports.LoadCallRequest(call_id="c1"))
        await database.close()

        assert [call.person_name for call in load_call_response.calls] == ["Grace"]

    async def test_a_call_id_is_issued_for_each_new_call(self) -> None:
        dsn = os.environ["CALLS_STORAGE"]
        database = pgdatabase_database.Database(pgdatabase_database.DatabaseRequest(dsn))
        await database.open()
        postgres_call_store = repositories.PostgresCallStore(database)

        async with postgres_call_store.transaction() as call_repository:
            issue_call_id_response = await call_repository.issue_call_id(ports.IssueCallIdRequest())
            other_issue_call_id_response = await call_repository.issue_call_id(ports.IssueCallIdRequest())
        await database.close()

        assert issue_call_id_response.call_id != other_issue_call_id_response.call_id
