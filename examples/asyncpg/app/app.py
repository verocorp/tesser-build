from __future__ import annotations

import tesser.app as ts

import alpha.adapters.gateways.beta_check as beta_check
import alpha.component.component as alpha_component
import beta.component.component as beta_component
import pgdatabase.database as pgdatabase

import app.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        databases: dict[str, pgdatabase.Database] = {}
        for coordinate in (cfg.alpha.storage, cfg.beta.storage):
            if coordinate.startswith(("postgres://", "postgresql://")) and coordinate not in databases:
                databases[coordinate] = pgdatabase.Database(coordinate)
        self.databases = tuple(databases.values())
        beta = beta_component.Beta(cfg.beta, databases.get(cfg.beta.storage))
        alpha = alpha_component.Alpha(
            cfg.alpha, databases.get(cfg.alpha.storage), beta_check.BetaCheckGateway(beta.client)
        )
        self.beta = beta
        self.alpha = alpha

    async def close(self) -> None:
        await self.alpha.close()
        await self.beta.close()
        for database in self.databases:
            await database.close()
