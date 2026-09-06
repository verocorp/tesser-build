from __future__ import annotations

import tesser.app as ts

import alpha.adapters.gateways as gateways
import alpha.component as alpha_component
import beta.component as beta_component

import app.config as config


class MinimalApp(ts.App):

    def __init__(self, app_config: config.AppConfig) -> None:
        beta = beta_component.Beta(app_config.beta)
        try:
            alpha = alpha_component.Alpha(app_config.alpha, gateways.BetaCheckGateway(beta.client))
        except Exception:
            beta.close()
            raise
        self.beta = beta
        self.alpha = alpha

    def close(self) -> None:
        self.alpha.close()
        self.beta.close()
