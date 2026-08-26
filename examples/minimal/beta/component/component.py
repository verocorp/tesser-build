from __future__ import annotations

import tesser.component as ts

import beta.adapters.repositories.memory as memory
import beta.application.beta_service as beta_service
import beta.client.client as client
import beta.component.config as config


class Beta(ts.Component):

    def __init__(self, cfg: config.Config) -> None:
        self._keys = memory.MemoryKeyRepository()
        self.client: client.Client = beta_service.BetaService(self._keys)

    def close(self) -> None:
        self._keys.close()
