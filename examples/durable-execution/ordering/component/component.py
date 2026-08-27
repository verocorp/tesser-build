from __future__ import annotations

import tesser.component as ts

import ordering.adapters.gateways.restate_quotes as restate_quotes
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
        self.quotes = restate_quotes.RestateQuotes()
        ingress = restate_workflow.RestateIngress(cfg.ingress)
        self.client: client.Client = order_service.OrderService(
            restate_workflow.RestateOrderWorkflow(ingress.send)
        )
        self.orchestrator: client.Orchestrator = order_orchestrator.OrderOrchestrator(self.quotes)
        self.actions: client.Actions = order_actions.OrderActions(self._catalog)

    def close(self) -> None:
        self._catalog.close()
