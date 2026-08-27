from __future__ import annotations

import asyncio
import collections.abc as abc

import tesser.component as ts
import httpx
import restate.client

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
        self._http = httpx.AsyncClient(base_url=cfg.ingress)
        self.client: client.Client = order_service.OrderService(
            restate_workflow.RestateOrderWorkflow(restate.client.Client(self._http))
        )

    def workflow(
        self, run: abc.Callable[[str, abc.Callable[[], abc.Coroutine[object, object, bytes]]], abc.Awaitable[bytes]]
    ) -> client.Orchestrator:
        return order_orchestrator.OrderOrchestrator(
            restate_repository.RestateCatalogRepository(self._catalog, run)
        )

    def close(self) -> None:
        asyncio.run(self._http.aclose())
        self._catalog.close()
