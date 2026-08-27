from __future__ import annotations

import tesser.component as ts
import httpx
import restate.client

import ordering.adapters.gateways.restate_actions as restate_actions
import ordering.adapters.gateways.restate_workflow as restate_workflow
import ordering.adapters.repositories.memory as memory
import ordering.application.order_actions as order_actions
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
        self.orchestrator: client.Orchestrator = order_orchestrator.OrderOrchestrator(
            restate_actions.RestateOrderActions()
        )
        self.actions: client.Actions = order_actions.OrderActions(self._catalog)

    async def close(self) -> None:
        await self._http.aclose()
        self._catalog.close()
