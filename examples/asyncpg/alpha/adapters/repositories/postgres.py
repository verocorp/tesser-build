from __future__ import annotations

import typing

import tesser.adapters as ts

import alpha.application.ports.widget_repository as widget_repository
import pgdatabase.database as pgdatabase

_SCHEMA: typing.Final[str] = "CREATE TABLE IF NOT EXISTS widgets (name text PRIMARY KEY)"
_SAVE: typing.Final[str] = "INSERT INTO widgets (name) VALUES ($1) ON CONFLICT (name) DO NOTHING"
_FIND: typing.Final[str] = "SELECT 1 FROM widgets WHERE name = $1"


class PostgresWidgetRepository(ts.Repository):

    def __init__(self, database: pgdatabase.Database) -> None:
        self._database = database
        self._schema_ready = False

    async def save(self, request: widget_repository.SaveRequest) -> widget_repository.SaveResponse:
        async with self._database.acquire() as connection, connection.transaction():
            if not self._schema_ready:
                await connection.execute(_SCHEMA)
                self._schema_ready = True
            await connection.execute(_SAVE, request.name)
        return widget_repository.SaveResponse(name=request.name)

    async def find(self, request: widget_repository.FindRequest) -> widget_repository.FindResponse:
        async with self._database.acquire() as connection, connection.transaction():
            if not self._schema_ready:
                await connection.execute(_SCHEMA)
                self._schema_ready = True
            row = await connection.fetchrow(_FIND, request.name)
        found = widget_repository.Found.NO if row is None else widget_repository.Found.YES
        return widget_repository.FindResponse(found=found)

    async def close(self) -> None:
        return None
