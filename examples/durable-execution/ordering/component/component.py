from __future__ import annotations

import tesser.component as ts

import ordering.adapters.gateways as gateways
import ordering.adapters.jobs as jobs
import ordering.adapters.repositories as repositories
import ordering.application as application
import ordering.client as client


class Spec(ts.Spec):

    def __init__(self, ingress: str) -> None:
        self.ingress = ingress


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.ingress = spec.ingress


class Ordering(ts.Component):

    def __init__(self, config: Config) -> None:
        self._catalog = repositories.MemoryCatalogRepository()
        self._actions = application.OrderActions(self._catalog)
        restate_action_jobs = jobs.RestateActionJobs(self._actions)
        restate_workflow_jobs = jobs.RestateWorkflowJobs(
            gateways.RestateQuoting(restate_action_jobs.quote)
        )
        self.jobs: tuple[jobs.RestateActionJobs, jobs.RestateWorkflowJobs] = (
            restate_action_jobs,
            restate_workflow_jobs,
        )
        self.client: client.OrderingClient = application.OrderService(
            gateways.RestateOrderWorkflow(config.ingress, restate_workflow_jobs.run)
        )

    def close(self) -> None:
        self._catalog.close()
