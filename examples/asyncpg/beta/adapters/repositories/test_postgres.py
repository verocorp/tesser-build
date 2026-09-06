from __future__ import annotations

import os

import asyncpg
import pytest

import beta.adapters.repositories as repositories
import beta.application.ports as ports
import pgdatabase.database as pgdatabase


class TestPostgresKeyStore:

    async def test_a_put_key_is_held_in_a_later_transaction(self) -> None:
        dsn = os.environ["BETA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS keys")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        postgres_key_store = repositories.PostgresKeyStore(database)
        async with postgres_key_store.transaction() as key_repository:
            put = await key_repository.put_key(ports.PutKeyRequest(key="k"))
        async with postgres_key_store.transaction() as key_repository:
            held = await key_repository.has_key(ports.HasKeyRequest(key="k"))
            missing = await key_repository.has_key(ports.HasKeyRequest(key="x"))
        await database.close()
        assert put.key == "k"
        assert held.held is ports.Held.YES
        assert missing.held is ports.Held.NO

    async def test_a_transaction_that_raises_is_rolled_back(self) -> None:
        dsn = os.environ["BETA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS keys")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        postgres_key_store = repositories.PostgresKeyStore(database)
        with pytest.raises(RuntimeError):
            async with postgres_key_store.transaction() as key_repository:
                await key_repository.put_key(ports.PutKeyRequest(key="k"))
                raise RuntimeError("abort")
        async with postgres_key_store.transaction() as key_repository:
            missing = await key_repository.has_key(ports.HasKeyRequest(key="k"))
        await database.close()
        assert missing.held is ports.Held.NO

    async def test_the_schema_outlives_a_first_transaction_that_rolls_back(self) -> None:
        dsn = os.environ["BETA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS keys")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        postgres_key_store = repositories.PostgresKeyStore(database)
        with pytest.raises(RuntimeError):
            async with postgres_key_store.transaction() as key_repository:
                await key_repository.put_key(ports.PutKeyRequest(key="k"))
                raise RuntimeError("abort")
        await database.close()
        connection = await asyncpg.connect(dsn)
        table = await connection.fetchval("SELECT to_regclass('keys') IS NOT NULL")
        await connection.close()
        assert table is True
