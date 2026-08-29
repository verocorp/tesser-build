from __future__ import annotations

import tesser.component as ts

import alpha.adapters.repositories.postgres as postgres
import alpha.application.alpha_service as alpha_service
import alpha.application.ports.beta_check as beta_check
import alpha.client.client as client
import alpha.component.config as config
import pgdatabase.database as pgdatabase


class Alpha(ts.Component):

    def __init__(self, cfg: config.Config, database: pgdatabase.Database, checks: beta_check.BetaCheck) -> None:
        self.client: client.Client = alpha_service.AlphaService(postgres.PostgresWidgetStore(database), checks)

    async def close(self) -> None:
        return None
