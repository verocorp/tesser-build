from __future__ import annotations

import asyncio
import contextlib
import typing

import asyncpg

_CLOSE_TIMEOUT_SECONDS: typing.Final[float] = 5.0


class Database:

    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 4) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool[asyncpg.Record] | None = None
        self._initializing = asyncio.Lock()

    @contextlib.asynccontextmanager
    async def acquire(self) -> typing.AsyncIterator[asyncpg.pool.PoolConnectionProxy[asyncpg.Record]]:
        async with self._initializing:
            if self._pool is None:
                self._pool = await asyncpg.create_pool(
                    self._dsn, min_size=self._min_size, max_size=self._max_size
                )
        async with self._pool.acquire() as connection:
            yield connection

    async def close(self) -> None:
        pool = self._pool
        self._pool = None
        if pool is None:
            return
        try:
            await asyncio.wait_for(pool.close(), timeout=_CLOSE_TIMEOUT_SECONDS)
        except TimeoutError:
            pool.terminate()
