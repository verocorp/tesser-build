from __future__ import annotations

import tesser.component as ts


class Spec(ts.Spec):

    def __init__(self, key: str) -> None:
        self.key = key


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.key = spec.key
