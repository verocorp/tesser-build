from __future__ import annotations

import tesser.component as ts

import beta.adapters.repositories as repositories
import beta.application as application
import beta.client as client
import pgdatabase.database as pgdatabase


class Spec(ts.Spec):

    def __init__(self, storage: str) -> None:
        self.storage = storage


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage
        self.database = pgdatabase.DatabaseRequest(spec.storage)


class Beta(ts.Component):

    def __init__(self, config: Config, database: pgdatabase.Database) -> None:
        self.client: client.BetaClient = application.BetaService(
            repositories.PostgresKeyStore(database)
        )

    async def close(self) -> None:
        return None
