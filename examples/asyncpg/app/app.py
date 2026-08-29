from __future__ import annotations

import tesser.app as ts

import alpha.adapters.gateways.beta_check as beta_check
import alpha.component.component as alpha_component
import beta.component.component as beta_component
import pgdatabase.database as pgdatabase

import app.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        self.databases = pgdatabase.Databases(cfg.alpha.database, cfg.beta.database)
        beta = beta_component.Beta(cfg.beta, self.databases.database(cfg.beta.database))
        alpha = alpha_component.Alpha(
            cfg.alpha, self.databases.database(cfg.alpha.database), beta_check.BetaCheckGateway(beta.client)
        )
        self.beta = beta
        self.alpha = alpha

    async def start(self) -> None:
        await self.databases.open()

    async def close(self) -> None:
        await self.alpha.close()
        await self.beta.close()
        await self.databases.close()
