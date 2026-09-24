from __future__ import annotations

import tesser.component as ts
import in_process

import alpha.adapters.activities as activities
import alpha.adapters.dispatchers as dispatchers
import alpha.adapters.repositories as repositories
import alpha.adapters.workflows as workflows
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
        self._widget_actions_service = in_process.Service("WidgetActions")
        self._widget_orchestrator_workflow = in_process.Workflow("WidgetOrchestrator")
        in_process_register_widget = workflows.InProcessRegisterWidget(
            self._widget_orchestrator_workflow,
            activities.InProcessKeepWidget(self._widget_actions_service, application.WidgetActions(self._widgets)),
        )
        self.client: client.AlphaClient = application.AlphaService(
            self._widgets,
            beta_check,
            dispatchers.InProcessWidgetOrchestratorRelay(
                in_process_register_widget, dispatchers.InProcessApproveWidget(self._widget_orchestrator_workflow)
            ),
        )

    def close(self) -> None:
        self._widgets.close()
