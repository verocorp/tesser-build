from __future__ import annotations

import tesser.component as ts


class Spec(ts.Spec):

    def __init__(self, keys: tuple[str, ...]) -> None:
        self.keys = keys


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.keys = spec.keys
