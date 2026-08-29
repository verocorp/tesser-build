from __future__ import annotations

import tesser.component as ts

import beta.adapters.repositories.postgres as postgres
import beta.application.beta_service as beta_service
import beta.client.client as client
import beta.component.config as config
import pgdatabase.database as pgdatabase


class Beta(ts.Component):

    def __init__(self, cfg: config.Config, database: pgdatabase.Database) -> None:
        self.client: client.Client = beta_service.BetaService(postgres.PostgresKeyStore(database))

    async def close(self) -> None:
        return None
