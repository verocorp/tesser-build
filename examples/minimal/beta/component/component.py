from __future__ import annotations

import tesser.component as ts

import beta.adapters.repositories as repositories
import beta.application as application
import beta.client as client
import beta.component.config as config


class Beta(ts.Component):

    def __init__(self, component_config: config.Config) -> None:
        self._keys = repositories.MemoryKeyRepository()
        self.client: client.Client = application.BetaService(self._keys)

    def close(self) -> None:
        self._keys.close()
