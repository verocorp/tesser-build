from __future__ import annotations

import typing

import asyncpg

import tesser.adapters as ts

import beta.application.ports.key_repository as key_repository

_SCHEMA: typing.Final[str] = "CREATE TABLE IF NOT EXISTS keys (key text PRIMARY KEY)"
_HAS: typing.Final[str] = "SELECT 1 FROM keys WHERE key = $1"
_PUT: typing.Final[str] = "INSERT INTO keys (key) VALUES ($1) ON CONFLICT (key) DO NOTHING"


class PostgresKeyRepository(ts.Repository):

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool[asyncpg.Record] | None = None

    async def has(self, request: key_repository.HasKeyRequest) -> key_repository.HasKeyResponse:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn)
            await self._pool.execute(_SCHEMA)
        row = await self._pool.fetchrow(_HAS, request.key)
        held = key_repository.Held.NO if row is None else key_repository.Held.YES
        return key_repository.HasKeyResponse(held=held)

    async def put(self, request: key_repository.PutKeyRequest) -> key_repository.PutKeyResponse:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn)
            await self._pool.execute(_SCHEMA)
        await self._pool.execute(_PUT, request.key)
        return key_repository.PutKeyResponse(key=request.key)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
