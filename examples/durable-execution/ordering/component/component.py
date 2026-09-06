from __future__ import annotations

import tesser.component as ts

import ordering.adapters.repositories as repositories
import ordering.adapters.runners as runners
import ordering.adapters.runtimes as runtimes
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
        self._memory_product_catalog_repository = repositories.MemoryProductCatalogRepository()
        self._order_actions = application.OrderActions(self._memory_product_catalog_repository)
        self.restate_order_runtime = runtimes.RestateOrderRuntime(self._order_actions)  # tesser:debt TB081
        self.client: client.OrderingClient = application.OrderService(
            runners.RestateOrderOrchestratorRunner(config.ingress, self.restate_order_runtime)
        )

    def close(self) -> None:
        self._memory_product_catalog_repository.close()
