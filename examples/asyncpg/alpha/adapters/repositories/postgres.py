from __future__ import annotations

import typing

import asyncpg

import tesser.adapters as ts

import alpha.application.ports.widget_repository as widget_repository

_SCHEMA: typing.Final[str] = "CREATE TABLE IF NOT EXISTS widgets (name text PRIMARY KEY)"
_SAVE: typing.Final[str] = "INSERT INTO widgets (name) VALUES ($1) ON CONFLICT (name) DO NOTHING"


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

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
