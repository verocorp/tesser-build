from __future__ import annotations

import asyncio
import contextlib
import typing

import asyncpg

_CLOSE_TIMEOUT_SECONDS: typing.Final[float] = 5.0
_POSTGRES_SCHEMES: typing.Final[tuple[str, ...]] = ("postgres://", "postgresql://")


class DatabaseRequest:

    def __init__(self, dsn: str) -> None:
        if not dsn.startswith(_POSTGRES_SCHEMES):
            raise ValueError(f"{dsn!r} is not a postgres DSN")
        self._dsn = dsn

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self._dsn == other._dsn

    def __hash__(self) -> int:
        return hash((type(self), self._dsn))

    def __str__(self) -> str:
        return self._dsn


class ClosablePool(typing.Protocol):

    async def close(self) -> None: ...

    def terminate(self) -> None: ...


async def close_pool(pool: ClosablePool, timeout: float) -> None:
    try:
        await asyncio.wait_for(pool.close(), timeout=timeout)
    except TimeoutError:
        pool.terminate()


class Database:

    def __init__(self, request: DatabaseRequest, min_size: int = 1, max_size: int = 4) -> None:
        self._dsn = str(request)
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool[asyncpg.Record] | None = None
        self._opening = asyncio.Lock()

    async def open(self) -> None:
        async with self._opening:
            if self._pool is not None:
                return
            self._pool = await asyncpg.create_pool(self._dsn, min_size=self._min_size, max_size=self._max_size)

    @contextlib.asynccontextmanager
    async def acquire(self) -> typing.AsyncIterator[asyncpg.pool.PoolConnectionProxy[asyncpg.Record]]:
        if self._pool is None:
            raise RuntimeError("the database is not open; the app opens its databases before serving")
        async with self._pool.acquire() as connection:
            yield connection

    async def close(self) -> None:
        pool = self._pool
        self._pool = None
        if pool is None:
            return
        await close_pool(pool, _CLOSE_TIMEOUT_SECONDS)


class Databases:

    def __init__(self, *requests: DatabaseRequest) -> None:
        self._by_request: dict[DatabaseRequest, Database] = {}
        for request in requests:
            if request not in self._by_request:
                self._by_request[request] = Database(request)

    def database(self, request: DatabaseRequest) -> Database:
        return self._by_request[request]

    def __len__(self) -> int:
        return len(self._by_request)

    async def open(self) -> None:
        opened: list[Database] = []
        try:
            for database in self._by_request.values():
                await database.open()
                opened.append(database)
        except BaseException:
            for database in opened:
                await database.close()
            raise

    async def close(self) -> None:
        for database in self._by_request.values():
            await database.close()
