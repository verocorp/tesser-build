from __future__ import annotations

import tesser.component as ts

import alpha.adapters.gateways.widget_quotes as widget_quotes
import alpha.adapters.jobs.engine as engine
import alpha.adapters.repositories.memory as memory
import alpha.application.alpha_service as alpha_service
import alpha.application.ports.beta_check as beta_check
import alpha.application.widget_actions as widget_actions
import alpha.client.client as client
import alpha.component.config as config
import tesser.errors as errors


class Alpha(ts.Component):

    def __init__(self, cfg: config.Config, checks: beta_check.BetaCheck) -> None:
        if cfg.storage != "memory":
            raise errors.invalid("unknown_backend", f"alpha storage {cfg.storage!r} not supported")
        self._widgets = memory.MemoryWidgetRepository()
        self._quotes = widget_quotes.WidgetQuoteGateway()
        self._actions = widget_actions.WidgetActions(self._widgets)
        self.client: client.Client = alpha_service.AlphaService(self._widgets, checks)
        self.jobs: engine.EngineJob = engine.EngineJob(self._actions, self._quotes)

    def close(self) -> None:
        self._widgets.close()
