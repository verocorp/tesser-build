from __future__ import annotations

import tesser.app as ts

import alpha.adapters.gateways.beta_check as beta_check
import alpha.component.component as alpha_component
import beta.component.component as beta_component

import app.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        beta = beta_component.Beta(cfg.beta)
        alpha = alpha_component.Alpha(cfg.alpha, beta_check.BetaCheckGateway(beta.client))
        self.beta = beta
        self.alpha = alpha

    async def close(self) -> None:
        await self.alpha.close()
        await self.beta.close()
