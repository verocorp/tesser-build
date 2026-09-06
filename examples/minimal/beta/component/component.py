from __future__ import annotations

import tesser.component as ts

import beta.adapters.repositories as repositories
import beta.application as application
import beta.client as client


class Spec(ts.Spec):

    def __init__(self, key: str) -> None:
        self.key = key


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.key = spec.key


class Beta(ts.Component):

    def __init__(self, config: Config) -> None:
        self._keys = repositories.MemoryKeyRepository()
        self.client: client.BetaClient = application.BetaService(self._keys)

    def close(self) -> None:
        self._keys.close()
