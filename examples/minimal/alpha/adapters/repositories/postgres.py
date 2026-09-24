from __future__ import annotations

import contextlib
import typing

import asyncpg

import tesser.adapters as ts

import alpha.application.ports as ports

_SCHEMA: typing.Final[str] = "CREATE TABLE IF NOT EXISTS widgets (name text PRIMARY KEY, standing text NOT NULL)"
_SAVE: typing.Final[str] = (
    "INSERT INTO widgets (name, standing) VALUES ($1, $2) ON CONFLICT (name) DO UPDATE SET standing = EXCLUDED.standing"
)
_FIND: typing.Final[str] = "SELECT 1 FROM widgets WHERE name = $1"


class PostgresWidgetRepository(ts.Repository):

    def __init__(self, connection: asyncpg.Connection[asyncpg.Record]) -> None:
        self._connection = connection

    async def save_widget(self, save_widget_request: ports.SaveWidgetRequest) -> ports.SaveWidgetResponse:
        await self._connection.execute(_SAVE, save_widget_request.name, save_widget_request.standing)
        return ports.SaveWidgetResponse(name=save_widget_request.name)

    async def find_widget(self, find_widget_request: ports.FindWidgetRequest) -> ports.FindWidgetResponse:
        row = await self._connection.fetchrow(_FIND, find_widget_request.name)
        outcome = ports.FindWidgetOutcome.NO if row is None else ports.FindWidgetOutcome.YES
        return ports.FindWidgetResponse(outcome=outcome)


class PostgresWidgetStore(ts.Repository):

    def __init__(self, storage: str) -> None:
        self._storage = storage

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.WidgetRepository]:
        connection = await asyncpg.connect(self._storage)
        try:
            await connection.execute(_SCHEMA)
            async with connection.transaction():
                yield PostgresWidgetRepository(connection)
        finally:
            await connection.close()
