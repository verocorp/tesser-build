from __future__ import annotations

import contextlib
import typing

import asyncpg

import tesser.adapters as ts

import alpha.application.ports as ports
import pgdatabase.database as pgdatabase

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

    async def add_widget(self, add_widget_request: ports.AddWidgetRequest) -> ports.AddWidgetResponse:
        try:
            added = await self._connection.fetchval(
                _ADD, add_widget_request.name, add_widget_request.part, add_widget_request.standing
            )
        except (asyncpg.PostgresError, OSError) as e:
            raise ports.StoreUnavailable("the widget store cannot answer") from e
        outcome = ports.Added.EXISTS if added is None else ports.Added.ADDED
        return ports.AddWidgetResponse(outcome=outcome, name=add_widget_request.name)

    async def save_widget(self, save_widget_request: ports.SaveWidgetRequest) -> ports.SaveWidgetResponse:
        try:
            await self._connection.execute(
                _SAVE, save_widget_request.name, save_widget_request.part, save_widget_request.standing
            )
        except (asyncpg.PostgresError, OSError) as e:
            raise ports.StoreUnavailable("the widget store cannot answer") from e
        return ports.SaveWidgetResponse(name=save_widget_request.name)

    async def load_widget(self, load_widget_request: ports.LoadWidgetRequest) -> ports.LoadWidgetResponse:
        try:
            row = await self._connection.fetchrow(_LOAD_FOR_UPDATE, load_widget_request.name)
        except (asyncpg.PostgresError, OSError) as e:
            raise ports.StoreUnavailable("the widget store cannot answer") from e
        if row is None:
            return ports.LoadWidgetResponse(outcome=ports.Loaded.MISSING, widgets=())
        return ports.LoadWidgetResponse(
            outcome=ports.Loaded.FOUND,
            widgets=(
                ports.WidgetRecord(
                    name=row["name"], part=row["part"], standing=row["standing"]
                ),
            ),
        )

    async def find_widget(self, find_widget_request: ports.FindWidgetRequest) -> ports.FindWidgetResponse:
        try:
            row = await self._connection.fetchrow(_FIND, find_widget_request.name)
        except (asyncpg.PostgresError, OSError) as e:
            raise ports.StoreUnavailable("the widget store cannot answer") from e
        found = ports.Found.NO if row is None else ports.Found.YES
        return ports.FindWidgetResponse(found=found)


class PostgresWidgetStore(ts.Repository):

    def __init__(self, database: pgdatabase.Database) -> None:
        self._database = database
        self._schema_ready = False

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.WidgetRepository]:
        async with self._database.acquire() as connection:
            if not self._schema_ready:
                try:
                    await connection.execute(_SCHEMA)
                    await connection.execute(_SCHEMA_STANDING)
                except (asyncpg.PostgresError, OSError) as e:
                    raise ports.StoreUnavailable("the widget store cannot answer") from e
                self._schema_ready = True
            async with connection.transaction():
                yield PostgresWidgetRepository(connection)
