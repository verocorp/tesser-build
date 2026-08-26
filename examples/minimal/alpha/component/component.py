from __future__ import annotations

import tesser.component as ts

import alpha.adapters.repositories.memory as memory
import alpha.application.alpha_service as alpha_service
import alpha.application.ports.beta_check as beta_check
import alpha.client.client as client
import alpha.component.config as config
import tesser.errors as errors


class Alpha(ts.Component):

    def __init__(self, cfg: config.Config, checks: beta_check.BetaCheck) -> None:
        if cfg.storage != "memory":
            raise errors.invalid("unknown_backend", f"alpha storage {cfg.storage!r} not supported")
        self._widgets = memory.MemoryWidgetRepository()
        self.client: client.Client = alpha_service.AlphaService(self._widgets, checks)

    def close(self) -> None:
        self._widgets.close()
