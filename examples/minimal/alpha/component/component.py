from __future__ import annotations

import tesser.component as ts

import alpha.adapters.gateways as gateways
import alpha.adapters.jobs as jobs
import alpha.adapters.repositories as repositories
import alpha.application as application
import alpha.application.ports as ports
import alpha.client as client
import alpha.component.config as config
import tesser.errors as errors


class Alpha(ts.Component):

    def __init__(self, component_config: config.Config, beta_check: ports.BetaCheck) -> None:
        if component_config.storage != "memory":
            raise errors.invalid("unknown_backend", f"alpha storage {component_config.storage!r} not supported")
        self._widgets = repositories.MemoryWidgetRepository()
        self._quotes = gateways.WidgetQuoteGateway()
        self._actions = application.WidgetActions(self._widgets)
        self.client: client.Client = application.AlphaService(self._widgets, beta_check)
        self.jobs: jobs.EngineJob = jobs.EngineJob(self._actions, self._quotes)

    def close(self) -> None:
        self._widgets.close()
