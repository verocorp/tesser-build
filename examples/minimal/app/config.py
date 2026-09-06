from __future__ import annotations

import tesser.app as ts

import alpha.component as alpha_component
import beta.component as beta_component


class Spec(ts.Spec):

    def __init__(self, alpha: alpha_component.Config, beta: beta_component.Config) -> None:
        self.alpha = alpha
        self.beta = beta


class AppConfig(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.alpha = spec.alpha
        self.beta = spec.beta
