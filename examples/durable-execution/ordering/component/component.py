from __future__ import annotations

import tesser.component as ts

import ordering.adapters.gateways.restate_quoting as restate_quoting
import ordering.adapters.gateways.restate_workflow as restate_workflow
import ordering.adapters.jobs.restate as restate_jobs
import ordering.adapters.repositories.memory as memory
import ordering.application.order_actions as order_actions
import ordering.application.order_service as order_service
import ordering.client.client as client
import ordering.component.config as config


class Ordering(ts.Component):

    def __init__(self, cfg: config.Config) -> None:
        self._catalog = memory.MemoryCatalogRepository()
        self._actions = order_actions.OrderActions(self._catalog)
        action_jobs = restate_jobs.RestateActionJobs(self._actions)
        workflow_jobs = restate_jobs.RestateWorkflowJobs(
            restate_quoting.RestateQuoting(action_jobs.quote)
        )
        self.jobs: tuple[restate_jobs.RestateActionJobs, restate_jobs.RestateWorkflowJobs] = (
            action_jobs,
            workflow_jobs,
        )
        self.client: client.Client = order_service.OrderService(
            restate_workflow.RestateOrderWorkflow(cfg.ingress, workflow_jobs.run)
        )

    def close(self) -> None:
        self._catalog.close()
