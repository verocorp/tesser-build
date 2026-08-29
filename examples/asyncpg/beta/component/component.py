from __future__ import annotations

import tesser.component as ts

import beta.adapters.repositories.memory as memory
import beta.adapters.repositories.postgres as postgres
import beta.application.beta_service as beta_service
import beta.client.client as client
import beta.component.config as config
import pgdatabase.database as pgdatabase
import tesser.errors as errors


class Beta(ts.Component):

    def __init__(self, cfg: config.Config, database: pgdatabase.Database | None) -> None:
        self._keys: memory.MemoryKeyRepository | postgres.PostgresKeyRepository
        if cfg.storage == "memory":
            self._keys = memory.MemoryKeyRepository()
        elif cfg.storage.startswith(("postgres://", "postgresql://")):
            if database is None:
                raise errors.invalid("missing_database", f"beta storage {cfg.storage!r} names a database the app did not build")
            self._keys = postgres.PostgresKeyRepository(database)
        else:
            raise errors.invalid("unknown_backend", f"beta storage {cfg.storage!r} not supported")
        self.client: client.Client = beta_service.BetaService(self._keys)

    async def close(self) -> None:
        await self._keys.close()
