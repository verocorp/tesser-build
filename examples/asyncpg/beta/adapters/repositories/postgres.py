from __future__ import annotations

import typing

import tesser.adapters as ts

import beta.application.ports.key_repository as key_repository
import pgdatabase.database as pgdatabase

_SCHEMA: typing.Final[str] = "CREATE TABLE IF NOT EXISTS keys (key text PRIMARY KEY)"
_HAS: typing.Final[str] = "SELECT 1 FROM keys WHERE key = $1"
_PUT: typing.Final[str] = "INSERT INTO keys (key) VALUES ($1) ON CONFLICT (key) DO NOTHING"


class PostgresKeyRepository(ts.Repository):

    def __init__(self, database: pgdatabase.Database) -> None:
        self._database = database
        self._schema_ready = False

    async def has(self, request: key_repository.HasKeyRequest) -> key_repository.HasKeyResponse:
        async with self._database.acquire() as connection, connection.transaction():
            if not self._schema_ready:
                await connection.execute(_SCHEMA)
                self._schema_ready = True
            row = await connection.fetchrow(_HAS, request.key)
        held = key_repository.Held.NO if row is None else key_repository.Held.YES
        return key_repository.HasKeyResponse(held=held)

    async def put(self, request: key_repository.PutKeyRequest) -> key_repository.PutKeyResponse:
        async with self._database.acquire() as connection, connection.transaction():
            if not self._schema_ready:
                await connection.execute(_SCHEMA)
                self._schema_ready = True
            await connection.execute(_PUT, request.key)
        return key_repository.PutKeyResponse(key=request.key)

    async def close(self) -> None:
        return None
