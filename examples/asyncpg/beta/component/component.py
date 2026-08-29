from __future__ import annotations

import tesser.component as ts

import beta.adapters.repositories.memory as memory
import beta.adapters.repositories.postgres as postgres
import beta.application.beta_service as beta_service
import beta.application.ports.key_repository as key_repository
import beta.client.client as client
import beta.component.config as config
import pgdatabase.database as pgdatabase
import tesser.errors as errors


class Beta(ts.Component):

    def __init__(self, cfg: config.Config, database: pgdatabase.Database | None) -> None:
        key_store: key_repository.KeyStore
        if cfg.database is None:
            key_store = memory.MemoryKeyStore()
        elif database is None:
            raise errors.invalid("missing_database", f"beta storage {cfg.storage!r} names a database the app did not build")
        else:
            key_store = postgres.PostgresKeyStore(database)
        self.client: client.Client = beta_service.BetaService(key_store)

    async def close(self) -> None:
        return None
