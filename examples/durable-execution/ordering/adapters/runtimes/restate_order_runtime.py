from __future__ import annotations

import tesser.adapters as ts
import restate
import restate.serde

import ordering.adapters.runners as runners
import ordering.application.client as client
import ordering.application.orchestrators as orchestrators
import ordering.application.ports as ports  # tesser:debt TB060
import ordering.application.relays as relays


class RestateOrderOrchestratorRequestSerde(
    ts.Serde, restate.serde.Serde[relays.OrderOrchestratorRequest]
):

    def serialize(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest | None
    ) -> bytes:
        if order_orchestrator_request is None:
            return b""
        return relays.OrderOrchestratorRequestSnapshot().serialize(order_orchestrator_request)

    def deserialize(self, buf: bytes) -> relays.OrderOrchestratorRequest | None:
        if not buf:
            raise ports.EngineRejected("a message crosses the engine with a body")
        return relays.OrderOrchestratorRequestSnapshot().deserialize(buf)


class RestateOrderOrchestratorResponseSerde(
    ts.Serde, restate.serde.Serde[relays.OrderOrchestratorResponse]
):

    def serialize(
        self, order_orchestrator_response: relays.OrderOrchestratorResponse | None
    ) -> bytes:
        if order_orchestrator_response is None:
            return b""
        return relays.OrderOrchestratorResponseSnapshot().serialize(order_orchestrator_response)

    def deserialize(self, buf: bytes) -> relays.OrderOrchestratorResponse | None:
        if not buf:
            raise ports.EngineRejected("a message crosses the engine with a body")
        return relays.OrderOrchestratorResponseSnapshot().deserialize(buf)


class RestatePriceProductRequestSerde(ts.Serde, restate.serde.Serde[relays.PriceProductRequest]):

    def serialize(self, price_product_request: relays.PriceProductRequest | None) -> bytes:
        if price_product_request is None:
            return b""
        return relays.PriceProductRequestSnapshot().serialize(price_product_request)

    def deserialize(self, buf: bytes) -> relays.PriceProductRequest | None:
        if not buf:
            raise ports.EngineRejected("a message crosses the engine with a body")
        return relays.PriceProductRequestSnapshot().deserialize(buf)


class RestatePriceProductResponseSerde(
    ts.Serde, restate.serde.Serde[relays.PriceProductResponse]
):

    def serialize(self, price_product_response: relays.PriceProductResponse | None) -> bytes:
        if price_product_response is None:
            return b""
        return relays.PriceProductResponseSnapshot().serialize(price_product_response)

    def deserialize(self, buf: bytes) -> relays.PriceProductResponse | None:
        if not buf:
            raise ports.EngineRejected("a message crosses the engine with a body")
        return relays.PriceProductResponseSnapshot().deserialize(buf)


class RestatePurchaseOrchestratorRequestSerde(
    ts.Serde, restate.serde.Serde[relays.PurchaseOrchestratorRequest]
):

    def serialize(
        self, purchase_orchestrator_request: relays.PurchaseOrchestratorRequest | None
    ) -> bytes:
        if purchase_orchestrator_request is None:
            return b""
        return relays.PurchaseOrchestratorRequestSnapshot().serialize(purchase_orchestrator_request)

    def deserialize(self, buf: bytes) -> relays.PurchaseOrchestratorRequest | None:
        if not buf:
            raise ports.EngineRejected("a message crosses the engine with a body")
        return relays.PurchaseOrchestratorRequestSnapshot().deserialize(buf)


class RestatePurchaseOrchestratorResponseSerde(
    ts.Serde, restate.serde.Serde[relays.PurchaseOrchestratorResponse]
):

    def serialize(
        self, purchase_orchestrator_response: relays.PurchaseOrchestratorResponse | None
    ) -> bytes:
        if purchase_orchestrator_response is None:
            return b""
        return relays.PurchaseOrchestratorResponseSnapshot().serialize(
            purchase_orchestrator_response
        )

    def deserialize(self, buf: bytes) -> relays.PurchaseOrchestratorResponse | None:
        if not buf:
            raise ports.EngineRejected("a message crosses the engine with a body")
        return relays.PurchaseOrchestratorResponseSnapshot().deserialize(buf)


class RestateTakePaymentRequestSerde(ts.Serde, restate.serde.Serde[relays.TakePaymentRequest]):

    def serialize(self, take_payment_request: relays.TakePaymentRequest | None) -> bytes:
        if take_payment_request is None:
            return b""
        return relays.TakePaymentRequestSnapshot().serialize(take_payment_request)

    def deserialize(self, buf: bytes) -> relays.TakePaymentRequest | None:
        if not buf:
            raise ports.EngineRejected("a message crosses the engine with a body")
        return relays.TakePaymentRequestSnapshot().deserialize(buf)


class RestateTakePaymentResponseSerde(ts.Serde, restate.serde.Serde[relays.TakePaymentResponse]):

    def serialize(self, take_payment_response: relays.TakePaymentResponse | None) -> bytes:
        if take_payment_response is None:
            return b""
        return relays.TakePaymentResponseSnapshot().serialize(take_payment_response)

    def deserialize(self, buf: bytes) -> relays.TakePaymentResponse | None:
        if not buf:
            raise ports.EngineRejected("a message crosses the engine with a body")
        return relays.TakePaymentResponseSnapshot().deserialize(buf)


class RestateOrderRuntime(ts.Runtime):

    def __init__(
        self,
        ordering_application_client: client.OrderingApplicationClient,
        purchase_application_client: client.PurchaseApplicationClient,
    ) -> None:
        self.order_actions_service = restate.Service("OrderActions")
        self.order_orchestrator_workflow = restate.Workflow("OrderOrchestrator")
        self.purchase_actions_service = restate.Service("PurchaseActions")
        self.purchase_orchestrator_workflow = restate.Workflow("PurchaseOrchestrator")

        @self.order_actions_service.handler(
            input_serde=RestatePriceProductRequestSerde(),
            output_serde=RestatePriceProductResponseSerde(),
        )
        async def price_product(  # tesser:debt TB023
            restate_context: restate.Context, price_product_request: relays.PriceProductRequest
        ) -> relays.PriceProductResponse:
            try:
                return ordering_application_client.price_product(price_product_request)
            except ports.EngineRejected as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=422
                ) from engine_error
            except ports.EngineMissing as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=404
                ) from engine_error
            except ports.EngineConflict as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=409
                ) from engine_error

        @self.order_orchestrator_workflow.main(
            input_serde=RestateOrderOrchestratorRequestSerde(),
            output_serde=RestateOrderOrchestratorResponseSerde(),
        )
        async def run(  # tesser:debt TB023
            restate_workflow_context: restate.WorkflowContext,
            order_orchestrator_request: relays.OrderOrchestratorRequest,
        ) -> relays.OrderOrchestratorResponse:
            try:
                return await orchestrators.OrderOrchestrator(
                    runners.RestateOrderActionsRunner(restate_workflow_context, self)
                ).run(order_orchestrator_request)
            except ports.EngineRejected as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=422
                ) from engine_error
            except ports.EngineMissing as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=404
                ) from engine_error
            except ports.EngineConflict as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=409
                ) from engine_error

        @self.purchase_actions_service.handler(
            input_serde=RestateTakePaymentRequestSerde(),
            output_serde=RestateTakePaymentResponseSerde(),
        )
        async def take_payment(  # tesser:debt TB023
            restate_context: restate.Context, take_payment_request: relays.TakePaymentRequest
        ) -> relays.TakePaymentResponse:
            try:
                return purchase_application_client.take_payment(take_payment_request)
            except ports.ChargeDeclined as declined:
                raise restate.TerminalError(
                    declined.message, status_code=409
                ) from declined
            except ports.EngineRejected as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=422
                ) from engine_error
            except ports.EngineMissing as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=404
                ) from engine_error
            except ports.EngineConflict as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=409
                ) from engine_error

        @self.purchase_orchestrator_workflow.main(
            name="run",
            input_serde=RestatePurchaseOrchestratorRequestSerde(),
            output_serde=RestatePurchaseOrchestratorResponseSerde(),
        )
        async def run_purchase(  # tesser:debt TB023
            restate_workflow_context: restate.WorkflowContext,
            purchase_orchestrator_request: relays.PurchaseOrchestratorRequest,
        ) -> relays.PurchaseOrchestratorResponse:
            try:
                return await orchestrators.PurchaseOrchestrator(
                    runners.RestatePurchaseActionsRunner(restate_workflow_context, self),
                    runners.RestateOrderOrchestratorChildRunner(restate_workflow_context, self),
                ).run(purchase_orchestrator_request)
            except ports.EngineRejected as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=422
                ) from engine_error
            except ports.EngineMissing as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=404
                ) from engine_error
            except ports.EngineConflict as engine_error:
                raise restate.TerminalError(
                    str(engine_error), status_code=409
                ) from engine_error

        self.price_product_handler = price_product
        self.order_orchestrator_handler = run
        self.take_payment_handler = take_payment
        self.purchase_orchestrator_handler = run_purchase
