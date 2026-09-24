from __future__ import annotations

import typing

import tesser.component as ts
import restate

import ordering.adapters.activities as activities
import ordering.adapters.dispatchers as dispatchers
import ordering.adapters.gateways as gateways
import ordering.adapters.repositories as repositories
import ordering.adapters.workflows as workflows
import ordering.application as application
import ordering.client as client

_RETRY_POLICY: typing.Final[restate.InvocationRetryPolicy] = restate.InvocationRetryPolicy(
    max_attempts=5, on_max_attempts="pause"
)


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

        async def make_order_payment(
            self, make_order_payment_request: client.MakeOrderPaymentRequest
        ) -> client.MakeOrderPaymentResponse:
            return await self._purchase_service.make_order_payment(make_order_payment_request)

    def __init__(self, config: Config) -> None:
        self._memory_product_catalog_repository = repositories.MemoryProductCatalogRepository()
        self._memory_payment_processor = gateways.MemoryPaymentProcessor()
        self.order_actions_service: restate.Service = restate.Service(
            "OrderActions", ingress_private=True, invocation_retry_policy=_RETRY_POLICY
        )
        self.purchase_actions_service: restate.Service = restate.Service(
            "PurchaseActions", ingress_private=True, invocation_retry_policy=_RETRY_POLICY
        )
        self.order_orchestrator_workflow: restate.Workflow = restate.Workflow(
            "OrderOrchestrator", invocation_retry_policy=_RETRY_POLICY
        )
        self.purchase_orchestrator_workflow: restate.Workflow = restate.Workflow(
            "PurchaseOrchestrator", invocation_retry_policy=_RETRY_POLICY
        )
        restate_price_product = activities.RestatePriceProduct(
            self.order_actions_service,
            application.OrderActions(self._memory_product_catalog_repository),
        )
        restate_take_payment = activities.RestateTakePayment(
            self.purchase_actions_service,
            application.PurchaseActions(self._memory_payment_processor),
        )
        restate_confirm_order = workflows.RestateConfirmOrder(
            self.order_orchestrator_workflow, restate_price_product
        )
        restate_pay_for_order = workflows.RestatePayForOrder(
            self.purchase_orchestrator_workflow, restate_take_payment, restate_confirm_order
        )
        self.client: client.OrderingClient = Ordering.Client(
            application.OrderService(
                dispatchers.RestateHttpOrderOrchestratorRelay(config.ingress, restate_confirm_order)
            ),
            application.PurchaseService(
                dispatchers.RestateHttpPurchaseOrchestratorRelay(config.ingress, restate_pay_for_order)
            ),
        )

    def close(self) -> None:
        self._memory_payment_processor.close()
        self._memory_product_catalog_repository.close()
