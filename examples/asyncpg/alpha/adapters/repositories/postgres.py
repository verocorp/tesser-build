from __future__ import annotations

import contextlib
import typing

import asyncpg

import tesser.adapters as ts

import alpha.application.ports.widget_repository as widget_repository
import pgdatabase.database as pgdatabase
import tesser.errors as errors

_SCHEMA: typing.Final[str] = (
    "CREATE TABLE IF NOT EXISTS widgets "
    "(name text PRIMARY KEY, part text NOT NULL, standing text NOT NULL DEFAULT 'kept')"
)
_SCHEMA_STANDING: typing.Final[str] = (
    "ALTER TABLE widgets ADD COLUMN IF NOT EXISTS standing text NOT NULL DEFAULT 'kept'"
)
_ADD: typing.Final[str] = (
    "INSERT INTO widgets (name, part, standing) VALUES ($1, $2, $3) "
    "ON CONFLICT (name) DO NOTHING RETURNING name"
)
_SAVE: typing.Final[str] = (
    "INSERT INTO widgets (name, part, standing) VALUES ($1, $2, $3) "
    "ON CONFLICT (name) DO UPDATE SET part = EXCLUDED.part, standing = EXCLUDED.standing"
)
_LOAD_FOR_UPDATE: typing.Final[str] = (
    "SELECT name, part, standing FROM widgets WHERE name = $1 FOR UPDATE"
)
_FIND: typing.Final[str] = "SELECT 1 FROM widgets WHERE name = $1"


class PostgresWidgetRepository(ts.Repository):

    def __init__(self, connection: asyncpg.pool.PoolConnectionProxy[asyncpg.Record]) -> None:
        self._connection = connection

    async def add_widget(self, request: widget_repository.AddWidgetRequest) -> widget_repository.AddWidgetResponse:
        added = await self._connection.fetchval(_ADD, request.name, request.part, request.standing)
        if added is None:
            raise errors.conflict("widget_exists", f"widget {request.name!r} is already stored")
        return widget_repository.AddWidgetResponse(name=request.name)

    async def save_widget(self, request: widget_repository.SaveWidgetRequest) -> widget_repository.SaveWidgetResponse:
        await self._connection.execute(_SAVE, request.name, request.part, request.standing)
        return widget_repository.SaveWidgetResponse(name=request.name)

    async def load_widget(self, request: widget_repository.LoadWidgetRequest) -> widget_repository.LoadWidgetResponse:
        row = await self._connection.fetchrow(_LOAD_FOR_UPDATE, request.name)
        if row is None:
            raise errors.not_found("unknown_widget", f"no widget {request.name!r}")
        return widget_repository.LoadWidgetResponse(
            name=row["name"], part=row["part"], standing=row["standing"]
        )

    async def find_widget(self, request: widget_repository.FindWidgetRequest) -> widget_repository.FindWidgetResponse:
        row = await self._connection.fetchrow(_FIND, request.name)
        found = widget_repository.Found.NO if row is None else widget_repository.Found.YES
        return widget_repository.FindWidgetResponse(found=found)


class PostgresWidgetStore(ts.Repository):

    def __init__(self, database: pgdatabase.Database) -> None:
        self._database = database
        self._schema_ready = False

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[widget_repository.WidgetRepository]:
        async with self._database.acquire() as connection:
            if not self._schema_ready:
                await connection.execute(_SCHEMA)
                await connection.execute(_SCHEMA_STANDING)
                self._schema_ready = True
            async with connection.transaction():
                yield PostgresWidgetRepository(connection)
