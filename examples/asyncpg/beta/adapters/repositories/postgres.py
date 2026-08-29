from __future__ import annotations

import contextlib
import typing

import asyncpg

import tesser.adapters as ts

import beta.application.ports.key_repository as key_repository
import pgdatabase.database as pgdatabase

_SCHEMA: typing.Final[str] = "CREATE TABLE IF NOT EXISTS keys (key text PRIMARY KEY)"
_HAS: typing.Final[str] = "SELECT 1 FROM keys WHERE key = $1"
_PUT: typing.Final[str] = "INSERT INTO keys (key) VALUES ($1) ON CONFLICT (key) DO NOTHING"


class PostgresKeyRepository(ts.Repository):

    def __init__(self, connection: asyncpg.pool.PoolConnectionProxy[asyncpg.Record]) -> None:
        self._connection = connection

    async def has_key(self, request: key_repository.HasKeyRequest) -> key_repository.HasKeyResponse:
        row = await self._connection.fetchrow(_HAS, request.key)
        held = key_repository.Held.NO if row is None else key_repository.Held.YES
        return key_repository.HasKeyResponse(held=held)

    async def put_key(self, request: key_repository.PutKeyRequest) -> key_repository.PutKeyResponse:
        await self._connection.execute(_PUT, request.key)
        return key_repository.PutKeyResponse(key=request.key)


class PostgresKeyStore(ts.Repository):

    def __init__(self, database: pgdatabase.Database) -> None:
        self._database = database
        self._schema_ready = False

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[key_repository.KeyRepository]:
        async with self._database.acquire() as connection:
            if not self._schema_ready:
                await connection.execute(_SCHEMA)
                self._schema_ready = True
            async with connection.transaction():
                yield PostgresKeyRepository(connection)
