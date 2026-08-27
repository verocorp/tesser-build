from __future__ import annotations

import tesser.component as ts


class Spec(ts.Spec):

    def __init__(self, ingress: str) -> None:
        self.ingress = ingress


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.ingress = spec.ingress
