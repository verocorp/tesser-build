from __future__ import annotations

import asyncio
import os
import time

import asyncpg
import pytest

import tesser.testing as ts

import pgdatabase.database as database

_COUNT_BACKENDS = "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid()"
_SETTLE_SECONDS = 2.0


@ts.helper
async def backends(dsn: str) -> int:
    connection = await asyncpg.connect(dsn)
    try:
        return int(await connection.fetchval(_COUNT_BACKENDS))
    finally:
        await connection.close()


@ts.helper
async def backends_settling_to(dsn: str, expected: int) -> int:
    deadline = time.monotonic() + _SETTLE_SECONDS
    counted = await backends(dsn)
    while counted != expected and time.monotonic() < deadline:
        await asyncio.sleep(0.05)
        counted = await backends(dsn)
    return counted


@ts.fake
class FakeHangingPool:

    def __init__(self) -> None:
        self.terminated = False

    async def close(self) -> None:
        await asyncio.sleep(_SETTLE_SECONDS * 100)

    def terminate(self) -> None:
        self.terminated = True


@ts.fake
class FakeClosingPool:

    def __init__(self) -> None:
        self.closed = False
        self.terminated = False

    async def close(self) -> None:
        self.closed = True

    def terminate(self) -> None:
        self.terminated = True


class TestDatabaseRequest:

    def test_two_requests_for_one_dsn_are_equal(self) -> None:
        assert database.DatabaseRequest("postgres://a@b/c") == database.DatabaseRequest("postgres://a@b/c")

    def test_a_non_postgres_dsn_is_refused(self) -> None:
        with pytest.raises(ValueError):
            database.DatabaseRequest("memory")


class TestClosePool:

    async def test_a_pool_that_will_not_close_in_time_is_terminated(self) -> None:
        pool = FakeHangingPool()
        async with asyncio.timeout(_SETTLE_SECONDS):
            await database.close_pool(pool, timeout=0.05)
        assert pool.terminated is True

    async def test_a_pool_that_closes_in_time_is_not_terminated(self) -> None:
        pool = FakeClosingPool()
        await database.close_pool(pool, timeout=_SETTLE_SECONDS)
        assert pool.closed is True
        assert pool.terminated is False


class TestDatabase:

    async def test_acquire_before_open_is_refused(self) -> None:
        db = database.Database(database.DatabaseRequest("postgres://nobody@nowhere/none"))
        with pytest.raises(RuntimeError):
            async with db.acquire():
                pass

    async def test_the_refusal_does_not_repeat_the_dsn(self) -> None:
        dsn = "postgres://nobody@nowhere/none"
        db = database.Database(database.DatabaseRequest(dsn))
        with pytest.raises(RuntimeError) as caught:
            async with db.acquire():
                pass
        assert dsn not in str(caught.value)
        assert "nowhere" not in str(caught.value)

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

    async def test_concurrent_opens_build_one_pool_and_orphan_nothing(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        db = database.Database(database.DatabaseRequest(dsn), min_size=2, max_size=2)
        baseline = await backends(dsn)
        await asyncio.gather(db.open(), db.open(), db.open())
        opened = await backends(dsn)
        await db.close()
        settled = await backends_settling_to(dsn, baseline)
        assert opened == baseline + 2
        assert settled == baseline

    async def test_a_close_that_races_an_open_closes_the_pool_that_open_built(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        db = database.Database(database.DatabaseRequest(dsn), min_size=2, max_size=2)
        baseline = await backends(dsn)
        await asyncio.gather(db.open(), db.close())
        settled = await backends_settling_to(dsn, baseline)
        with pytest.raises(RuntimeError):
            async with db.acquire():
                pass
        assert settled == baseline

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

    def test_one_database_per_distinct_request(self) -> None:
        shared = database.DatabaseRequest("postgres://a@b/one")
        other = database.DatabaseRequest("postgres://a@b/two")
        databases = database.Databases(shared, database.DatabaseRequest("postgres://a@b/one"), other)
        assert len(databases) == 2
        assert databases.database(shared) is databases.database(database.DatabaseRequest("postgres://a@b/one"))
        assert databases.database(other) is not databases.database(shared)

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

    async def test_an_open_that_fails_part_way_closes_what_it_opened(self) -> None:
        dsn = os.environ["ALPHA_STORAGE"]
        reachable = database.DatabaseRequest(dsn)
        unreachable = database.DatabaseRequest("postgres://nobody@127.0.0.1:1/none")
        databases = database.Databases(reachable, unreachable)
        baseline = await backends(dsn)
        with pytest.raises(OSError):
            await databases.open()
        settled = await backends_settling_to(dsn, baseline)
        with pytest.raises(RuntimeError):
            async with databases.database(reachable).acquire():
                pass
        assert settled == baseline
