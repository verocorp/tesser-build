from __future__ import annotations

import asyncio
import os

import pytest

import pgdatabase.database as database


class TestDatabaseRequest:

    def test_two_requests_for_one_dsn_are_equal(self) -> None:
        assert database.DatabaseRequest("postgres://a@b/c") == database.DatabaseRequest("postgres://a@b/c")

    def test_a_non_postgres_dsn_is_refused(self) -> None:
        with pytest.raises(ValueError):
            database.DatabaseRequest("memory")


class TestDatabase:

    async def test_acquire_before_open_is_refused(self) -> None:
        db = database.Database(database.DatabaseRequest("postgres://nobody@nowhere/none"))
        with pytest.raises(RuntimeError):
            async with db.acquire():
                pass

    async def test_open_connects_and_acquire_reuses_the_pool(self) -> None:
        db = database.Database(database.DatabaseRequest(os.environ["ALPHA_STORAGE"]))
        await db.open()
        async with db.acquire() as first:
            first_pid = await first.fetchval("SELECT pg_backend_pid()")
        async with db.acquire() as second:
            second_pid = await second.fetchval("SELECT pg_backend_pid()")
        await db.close()
        assert first_pid == second_pid

    async def test_open_is_idempotent(self) -> None:
        db = database.Database(database.DatabaseRequest(os.environ["ALPHA_STORAGE"]))
        await db.open()
        await db.open()
        async with db.acquire() as connection:
            value = await connection.fetchval("SELECT 1")
        await db.close()
        assert value == 1

    async def test_open_fails_at_open_when_the_database_is_unreachable(self) -> None:
        db = database.Database(database.DatabaseRequest("postgres://nobody@127.0.0.1:1/none"))
        with pytest.raises(OSError):
            await db.open()

    async def test_close_before_open_is_a_no_op_and_close_is_idempotent(self) -> None:
        db = database.Database(database.DatabaseRequest(os.environ["ALPHA_STORAGE"]))
        await db.close()
        await db.open()
        await db.close()
        await db.close()

    async def test_a_cancelled_query_releases_its_connection(self) -> None:
        db = database.Database(database.DatabaseRequest(os.environ["ALPHA_STORAGE"]), min_size=1, max_size=1)
        await db.open()

        async def slow() -> None:
            async with db.acquire() as connection:
                await connection.execute("SELECT pg_sleep(10)")

        task = asyncio.create_task(slow())
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        async with asyncio.timeout(2.0):
            async with db.acquire() as connection:
                value = await connection.fetchval("SELECT 1")
        await db.close()
        assert value == 1


class TestDatabases:

    def test_one_database_per_distinct_request_and_none_for_no_request(self) -> None:
        shared = database.DatabaseRequest("postgres://a@b/one")
        other = database.DatabaseRequest("postgres://a@b/two")
        databases = database.Databases(shared, None, database.DatabaseRequest("postgres://a@b/one"), other)
        assert len(databases) == 2
        assert databases.database(shared) is databases.database(database.DatabaseRequest("postgres://a@b/one"))
        assert databases.database(other) is not databases.database(shared)
        assert databases.database(None) is None

    async def test_open_and_close_reach_every_database(self) -> None:
        request = database.DatabaseRequest(os.environ["ALPHA_STORAGE"])
        databases = database.Databases(request)
        await databases.open()
        db = databases.database(request)
        assert db is not None
        async with db.acquire() as connection:
            value = await connection.fetchval("SELECT 1")
        await databases.close()
        with pytest.raises(RuntimeError):
            async with db.acquire():
                pass
        assert value == 1
