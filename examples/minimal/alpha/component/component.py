from __future__ import annotations

import tesser.component as ts

import alpha.adapters.gateways.beta_check as beta_check
import alpha.adapters.repositories.memory as memory
import alpha.application.service as service
import alpha.client.client as client
import alpha.component.config as config
import beta.client.client as beta_client
import tesser.errors as errors


class Alpha(ts.Component):

    def __init__(self, cfg: config.Config, beta: beta_client.Client) -> None:
        if cfg.storage != "memory":
            raise errors.invalid("unknown_backend", f"alpha storage {cfg.storage!r} not supported")
        self._wholes = memory.MemoryWholeRepository()
        self.client: client.Client = service.AlphaService(self._wholes, beta_check.BetaCheckGateway(beta))

    def close(self) -> None:
        self._wholes.close()
