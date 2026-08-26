from __future__ import annotations

import tesser.app as ts

import alpha.component.component as alpha_component
import beta.component.component as beta_component

import app.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        beta = beta_component.Beta(cfg.beta)
        try:
            alpha = alpha_component.Alpha(cfg.alpha, beta.client)
        except Exception:
            beta.close()
            raise
        self.beta = beta
        self.alpha = alpha

    def close(self) -> None:
        self.alpha.close()
        self.beta.close()
