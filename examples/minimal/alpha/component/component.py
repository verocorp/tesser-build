from __future__ import annotations

import tesser.component as ts

import alpha.adapters.repositories as repositories
import alpha.adapters.runtimes as runtimes
import alpha.application as application
import alpha.application.ports as ports
import alpha.client as client
import tesser.errors as errors


class Spec(ts.Spec):

    def __init__(self, storage: str) -> None:
        self.storage = storage


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage


class Alpha(ts.Component):

    def __init__(self, config: Config, beta_check: ports.BetaCheck) -> None:
        if config.storage != "memory":
            raise errors.invalid("unknown_backend", f"alpha storage {config.storage!r} not supported")
        self._widgets = repositories.MemoryWidgetRepository()
        self._actions = application.WidgetActions(self._widgets)
        self.client: client.AlphaClient = application.AlphaService(self._widgets, beta_check)
        self.inline_widget_runtime: runtimes.InlineWidgetRuntime = runtimes.InlineWidgetRuntime(self._actions)

    def close(self) -> None:
        self._widgets.close()
