from __future__ import annotations

import tesser.app as ts

import alpha.component.config as alpha_config
import beta.component.config as beta_config


class Spec(ts.Spec):

    def __init__(self, alpha: alpha_config.Config, beta: beta_config.Config) -> None:
        self.alpha = alpha
        self.beta = beta


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.alpha = spec.alpha
        self.beta = spec.beta
