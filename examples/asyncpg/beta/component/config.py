from __future__ import annotations

import tesser.component as ts

import pgdatabase.database as pgdatabase


class Spec(ts.Spec):

    def __init__(self, storage: str) -> None:
        self.storage = storage


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage
        self.database = pgdatabase.DatabaseRequest(spec.storage)
