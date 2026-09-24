from __future__ import annotations

import typing

import tesser.component as ts
import restate

import alpha.adapters.activities as activities
import alpha.adapters.dispatchers as dispatchers
import alpha.adapters.repositories as repositories
import alpha.adapters.workflows as workflows
import alpha.application as application
import alpha.application.ports as ports
import alpha.client as client
import tesser.errors as errors

_RETRY_POLICY: typing.Final[restate.InvocationRetryPolicy] = restate.InvocationRetryPolicy(
    max_attempts=5, on_max_attempts="pause"
)


class Spec(ts.Spec):

    def __init__(self, storage: str, ingress: str) -> None:
        self.storage = storage
        self.ingress = ingress


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage
        self.ingress = spec.ingress


class Alpha(ts.Component):

    def __init__(self, config: Config, beta_check: ports.BetaCheck) -> None:
        if not config.storage.startswith("postgres://"):
            raise errors.invalid("unknown_backend", f"alpha storage {config.storage!r} not supported")
        self._postgres_widget_store = repositories.PostgresWidgetStore(config.storage)
        self.widget_actions_service: restate.Service = restate.Service(
            "WidgetActions", ingress_private=True, invocation_retry_policy=_RETRY_POLICY
        )
        self.widget_orchestrator_workflow: restate.Workflow = restate.Workflow(
            "WidgetOrchestrator", invocation_retry_policy=_RETRY_POLICY
        )
        restate_register_widget = workflows.RestateRegisterWidget(
            self.widget_orchestrator_workflow,
            activities.RestateKeepWidget(self.widget_actions_service, application.WidgetActions(self._postgres_widget_store)),
        )
        self.client: client.AlphaClient = application.AlphaService(
            self._postgres_widget_store,
            beta_check,
            dispatchers.RestateHttpWidgetOrchestratorRelay(
                config.ingress,
                restate_register_widget,
                dispatchers.RestateApproveWidget(self.widget_orchestrator_workflow),
            ),
        )

    def close(self) -> None:
        return None
