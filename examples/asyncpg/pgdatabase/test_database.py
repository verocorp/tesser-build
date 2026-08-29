from __future__ import annotations

import asyncio
import os

import pytest

import pgdatabase.database as database


class TestDatabase:

    async def test_the_pool_is_created_on_first_acquire_and_reused(self) -> None:
        db = database.Database(os.environ["ALPHA_STORAGE"])
        async with db.acquire() as first:
            first_pid = await first.fetchval("SELECT pg_backend_pid()")
        async with db.acquire() as second:
            second_pid = await second.fetchval("SELECT pg_backend_pid()")
        await db.close()
        assert first_pid == second_pid

    async def test_concurrent_first_acquires_create_one_pool(self) -> None:
        db = database.Database(os.environ["ALPHA_STORAGE"], min_size=1, max_size=2)

        async def one() -> int:
            async with db.acquire() as connection:
                pid: int = await connection.fetchval("SELECT pg_backend_pid()")
                await asyncio.sleep(0.05)
                return pid

        pids = await asyncio.gather(one(), one(), one())
        await db.close()
        assert len(set(pids)) <= 2

    async def test_close_before_any_acquire_is_a_no_op(self) -> None:
        db = database.Database("postgres://nobody@nowhere/none")
        await db.close()

    async def test_close_is_idempotent(self) -> None:
        db = database.Database(os.environ["ALPHA_STORAGE"])
        async with db.acquire() as connection:
            await connection.fetchval("SELECT 1")
        await db.close()
        await db.close()

    async def test_a_cancelled_query_releases_its_connection(self) -> None:
        db = database.Database(os.environ["ALPHA_STORAGE"], min_size=1, max_size=1)

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
