from __future__ import annotations

import collections.abc as abc

import tesser.component as ts

import ordering.adapters.gateways.restate_workflow as restate_workflow
import ordering.adapters.repositories.memory as memory
import ordering.adapters.repositories.restate as restate_repository
import ordering.application.order_orchestrator as order_orchestrator
import ordering.application.order_service as order_service
import ordering.client.client as client
import ordering.component.config as config


class Ordering(ts.Component):

    def __init__(self, cfg: config.Config) -> None:
        self._catalog = memory.MemoryCatalogRepository()
        ingress = restate_workflow.RestateIngress(cfg.ingress)
        self.client: client.Client = order_service.OrderService(
            restate_workflow.RestateOrderWorkflow(ingress.send)
        )

    def workflow(
        self, run: abc.Callable[[str, abc.Callable[[], abc.Coroutine[object, object, bytes]]], abc.Awaitable[bytes]]
    ) -> client.Orchestrator:
        return order_orchestrator.OrderOrchestrator(
            restate_repository.RestateCatalogRepository(self._catalog, run)
        )

    def close(self) -> None:
        self._catalog.close()
