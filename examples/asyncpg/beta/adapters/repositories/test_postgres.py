from __future__ import annotations

import os

import asyncpg
import pytest

import beta.adapters.repositories.postgres as postgres
import beta.application.ports.key_repository as key_repository
import pgdatabase.database as pgdatabase


class TestPostgresKeyStore:

    async def test_a_put_key_is_held_in_a_later_transaction(self) -> None:
        dsn = os.environ["BETA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS keys")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        key_store = postgres.PostgresKeyStore(database)
        async with key_store.transaction() as keys_repo:
            put = await keys_repo.put_key(key_repository.PutKeyRequest(key="k"))
        async with key_store.transaction() as keys_repo:
            held = await keys_repo.has_key(key_repository.HasKeyRequest(key="k"))
            missing = await keys_repo.has_key(key_repository.HasKeyRequest(key="x"))
        await database.close()
        assert put.key == "k"
        assert held.held is key_repository.Held.YES
        assert missing.held is key_repository.Held.NO

    async def test_a_transaction_that_raises_is_rolled_back(self) -> None:
        dsn = os.environ["BETA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS keys")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        key_store = postgres.PostgresKeyStore(database)
        with pytest.raises(RuntimeError):
            async with key_store.transaction() as keys_repo:
                await keys_repo.put_key(key_repository.PutKeyRequest(key="k"))
                raise RuntimeError("abort")
        async with key_store.transaction() as keys_repo:
            missing = await keys_repo.has_key(key_repository.HasKeyRequest(key="k"))
        await database.close()
        assert missing.held is key_repository.Held.NO

    async def test_the_schema_outlives_a_first_transaction_that_rolls_back(self) -> None:
        dsn = os.environ["BETA_STORAGE"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS keys")
        await connection.close()
        database = pgdatabase.Database(pgdatabase.DatabaseRequest(dsn))
        await database.open()
        key_store = postgres.PostgresKeyStore(database)
        with pytest.raises(RuntimeError):
            async with key_store.transaction() as keys_repo:
                await keys_repo.put_key(key_repository.PutKeyRequest(key="k"))
                raise RuntimeError("abort")
        await database.close()
        connection = await asyncpg.connect(dsn)
        table = await connection.fetchval("SELECT to_regclass('keys') IS NOT NULL")
        await connection.close()
        assert table is True
