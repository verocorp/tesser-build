from __future__ import annotations

import os

import asyncpg

import beta.adapters.repositories.postgres as postgres
import beta.application.ports.key_repository as key_repository


class TestPostgresKeyRepository:

    async def test_a_put_key_is_held_across_repositories(self) -> None:
        dsn = os.environ["ASYNCPG_DSN"]
        connection = await asyncpg.connect(dsn)
        await connection.execute("DROP TABLE IF EXISTS keys")
        await connection.close()
        writer = postgres.PostgresKeyRepository(dsn)
        put = await writer.put(key_repository.PutKeyRequest(key="k"))
        await writer.close()
        reader = postgres.PostgresKeyRepository(dsn)
        held = await reader.has(key_repository.HasKeyRequest(key="k"))
        missing = await reader.has(key_repository.HasKeyRequest(key="x"))
        await reader.close()
        assert put.key == "k"
        assert held.held is key_repository.Held.YES
        assert missing.held is key_repository.Held.NO
