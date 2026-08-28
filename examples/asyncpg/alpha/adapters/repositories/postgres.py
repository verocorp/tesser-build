from __future__ import annotations

import typing

import asyncpg

import tesser.adapters as ts

import alpha.application.ports.widget_repository as widget_repository

_SCHEMA: typing.Final[str] = "CREATE TABLE IF NOT EXISTS widgets (name text PRIMARY KEY)"
_SAVE: typing.Final[str] = "INSERT INTO widgets (name) VALUES ($1) ON CONFLICT (name) DO NOTHING"
_FIND: typing.Final[str] = "SELECT 1 FROM widgets WHERE name = $1"


class PostgresWidgetRepository(ts.Repository):

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool[asyncpg.Record] | None = None

    async def save(self, request: widget_repository.SaveRequest) -> widget_repository.SaveResponse:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn)
            await self._pool.execute(_SCHEMA)
        await self._pool.execute(_SAVE, request.name)
        return widget_repository.SaveResponse(name=request.name)

    async def find(self, request: widget_repository.FindRequest) -> widget_repository.FindResponse:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn)
            await self._pool.execute(_SCHEMA)
        row = await self._pool.fetchrow(_FIND, request.name)
        found = widget_repository.Found.NO if row is None else widget_repository.Found.YES
        return widget_repository.FindResponse(found=found)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
