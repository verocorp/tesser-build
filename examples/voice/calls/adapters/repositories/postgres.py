from __future__ import annotations

import contextlib
import typing

import asyncpg

import tesser.adapters as ts

import calls.application.ports as ports
import pgdatabase.database as pgdatabase_database

_SCHEMA: typing.Final[str] = (
    "CREATE TABLE IF NOT EXISTS calls "
    "(call_id text PRIMARY KEY, person_name text NOT NULL, phone_number text NOT NULL)"
)
_SAVE: typing.Final[str] = "INSERT INTO calls (call_id, person_name, phone_number) VALUES ($1, $2, $3)"
_LOAD: typing.Final[str] = "SELECT call_id, person_name, phone_number FROM calls WHERE call_id = $1"


class PostgresCallRepository(ts.Repository):

    def __init__(self, connection: asyncpg.pool.PoolConnectionProxy[asyncpg.Record]) -> None:
        self._connection = connection

    async def save_call(self, save_call_request: ports.SaveCallRequest) -> ports.SaveCallResponse:
        await self._connection.execute(
            _SAVE,
            save_call_request.call_id,
            save_call_request.person_name,
            save_call_request.phone_number,
        )
        return ports.SaveCallResponse(call_id=save_call_request.call_id)

    async def load_call(self, load_call_request: ports.LoadCallRequest) -> ports.LoadCallResponse:
        rows = await self._connection.fetch(_LOAD, load_call_request.call_id)
        outcome = ports.LoadCallOutcome.NOT_FOUND if rows == [] else ports.LoadCallOutcome.FOUND
        return ports.LoadCallResponse(
            outcome=outcome,
            calls=tuple(
                ports.Call(call_id=row["call_id"], person_name=row["person_name"], phone_number=row["phone_number"])
                for row in rows
            ),
        )


class PostgresCallStore(ts.Repository):

    def __init__(self, database: pgdatabase_database.Database) -> None:
        self._database = database
        self._schema_ready = False

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.CallRepository]:
        async with self._database.acquire() as connection:
            if not self._schema_ready:
                await connection.execute(_SCHEMA)
                self._schema_ready = True
            async with connection.transaction():
                yield PostgresCallRepository(connection)
