from __future__ import annotations

import tesser.component as ts

import calls.adapters.repositories as repositories
import calls.adapters.runners as runners
import calls.adapters.runtimes as runtimes
import calls.application as application
import calls.client as client
import pgdatabase.database as pgdatabase_database


class Spec(ts.Spec):

    def __init__(self, storage: str, ingress: str) -> None:
        self.storage = storage
        self.ingress = ingress


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage
        self.ingress = spec.ingress
        self.database = pgdatabase_database.DatabaseRequest(spec.storage)


class Calls(ts.Component):

    def __init__(self, config: Config, database: pgdatabase_database.Database) -> None:
        self._postgres_call_store = repositories.PostgresCallStore(database)
        self.restate_call_runtime: runtimes.RestateCallRuntime = runtimes.RestateCallRuntime(
            application.CallActions(self._postgres_call_store)
        )
        self.client: client.CallsClient = application.CallsService(
            runners.RestateIngressConductCallRelay(config.ingress, self.restate_call_runtime),
            self._postgres_call_store,
        )

    async def close(self) -> None:
        return None
