from __future__ import annotations

import tesser.component as ts

import calls.adapters.repositories as repositories
import calls.application as application
import calls.client as client
import pgdatabase.database as pgdatabase_database


class Spec(ts.Spec):

    def __init__(self, storage: str) -> None:
        self.storage = storage


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage
        self.database = pgdatabase_database.DatabaseRequest(spec.storage)


class Calls(ts.Component):

    def __init__(self, config: Config, database: pgdatabase_database.Database) -> None:
        self.client: client.CallsClient = application.CallsService(repositories.PostgresCallStore(database))

    async def close(self) -> None:
        return None
