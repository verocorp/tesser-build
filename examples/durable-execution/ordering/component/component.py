from __future__ import annotations

import tesser.component as ts

import ordering.adapters.gateways as gateways
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

    class Client:

        def __init__(
            self,
            order_service: application.OrderService,
            purchase_service: application.PurchaseService,
        ) -> None:
            self._order_service = order_service
            self._purchase_service = purchase_service

        async def submit_order(
            self, submit_order_request: client.SubmitOrderRequest
        ) -> client.SubmitOrderResponse:
            return await self._order_service.submit_order(submit_order_request)

        async def place_order(
            self, place_order_request: client.PlaceOrderRequest
        ) -> client.PlaceOrderResponse:
            return await self._order_service.place_order(place_order_request)

        async def purchase(self, purchase_request: client.PurchaseRequest) -> client.PurchaseResponse:
            return await self._purchase_service.purchase(purchase_request)

    def __init__(self, config: Config) -> None:
        self._memory_product_catalog_repository = repositories.MemoryProductCatalogRepository()
        self._order_actions = application.OrderActions(self._memory_product_catalog_repository)
        self._memory_payment_processor = gateways.MemoryPaymentProcessor()
        self._purchase_actions = application.PurchaseActions(self._memory_payment_processor)
        self.restate_order_runtime: runtimes.RestateOrderRuntime = runtimes.RestateOrderRuntime(
            self._order_actions, self._purchase_actions
        )
        self.client: client.OrderingClient = Ordering.Client(
            application.OrderService(
                runners.RestateOrderOrchestratorRunner(config.ingress, self.restate_order_runtime)
            ),
            application.PurchaseService(
                runners.RestatePurchaseOrchestratorRunner(config.ingress, self.restate_order_runtime)
            ),
        )

    def close(self) -> None:
        self._memory_payment_processor.close()
        self._memory_product_catalog_repository.close()
