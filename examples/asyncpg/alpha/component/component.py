from __future__ import annotations

import tesser.component as ts

import alpha.adapters.repositories as repositories
import alpha.application as application
import alpha.application.ports as ports
import alpha.client as client
import pgdatabase.database as pgdatabase_database


class Spec(ts.Spec):

    def __init__(self, storage: str) -> None:
        self.storage = storage


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage
        self.database = pgdatabase_database.DatabaseRequest(spec.storage)


class Alpha(ts.Component):

    def __init__(
        self, config: Config, database: pgdatabase_database.Database, beta_check: ports.BetaCheck
    ) -> None:
        self.client: client.AlphaClient = application.AlphaService(
            repositories.PostgresWidgetStore(database), beta_check
        )

    async def close(self) -> None:
        return None
