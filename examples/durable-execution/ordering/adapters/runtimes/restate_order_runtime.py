from __future__ import annotations  # tesser:debt TB041

import tesser.adapters as ts
import restate
import restate.serde

import ordering.adapters.runners as runners
import ordering.application.client as client  # tesser:debt TB060
import ordering.application.orchestrators as orchestrators  # tesser:debt TB060
import ordering.application.relays as relays  # tesser:debt TB060
import tesser.errors as errors


class RestateOrderOrchestratorRequestSerde(  # tesser:debt TB081
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
            raise errors.invalid("empty_message", "a message crosses the engine with a body")
        return relays.OrderOrchestratorRequestSnapshot().deserialize(buf)


class RestateOrderOrchestratorResponseSerde(  # tesser:debt TB081
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
            raise errors.invalid("empty_message", "a message crosses the engine with a body")
        return relays.OrderOrchestratorResponseSnapshot().deserialize(buf)


class RestatePriceProductRequestSerde(ts.Serde, restate.serde.Serde[relays.PriceProductRequest]):  # tesser:debt TB081

    def serialize(self, price_product_request: relays.PriceProductRequest | None) -> bytes:
        if price_product_request is None:
            return b""
        return relays.PriceProductRequestSnapshot().serialize(price_product_request)

    def deserialize(self, buf: bytes) -> relays.PriceProductRequest | None:
        if not buf:
            raise errors.invalid("empty_message", "a message crosses the engine with a body")
        return relays.PriceProductRequestSnapshot().deserialize(buf)


class RestatePriceProductResponseSerde(  # tesser:debt TB081
    ts.Serde, restate.serde.Serde[relays.PriceProductResponse]
):

    def serialize(self, price_product_response: relays.PriceProductResponse | None) -> bytes:
        if price_product_response is None:
            return b""
        return relays.PriceProductResponseSnapshot().serialize(price_product_response)

    def deserialize(self, buf: bytes) -> relays.PriceProductResponse | None:
        if not buf:
            raise errors.invalid("empty_message", "a message crosses the engine with a body")
        return relays.PriceProductResponseSnapshot().deserialize(buf)


class RestateOrderRuntime(ts.Job):

    def __init__(self, ordering_application_client: client.OrderingApplicationClient) -> None:
        self.order_actions_service = restate.Service("OrderActions")
        self.order_orchestrator_workflow = restate.Workflow("OrderOrchestrator")

        @self.order_actions_service.handler(
            input_serde=RestatePriceProductRequestSerde(),
            output_serde=RestatePriceProductResponseSerde(),
        )
        async def price_product(  # tesser:debt TB023
            restate_context: restate.Context, price_product_request: relays.PriceProductRequest
        ) -> relays.PriceProductResponse:
            try:
                return ordering_application_client.price_product(price_product_request)
            except errors.DomainError as domain_error:
                raise restate.TerminalError(
                    domain_error.message, status_code=errors.status_for(domain_error.kind)
                ) from domain_error

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
            except errors.DomainError as domain_error:
                raise restate.TerminalError(
                    domain_error.message, status_code=errors.status_for(domain_error.kind)
                ) from domain_error

        self.price_product_handler = price_product
        self.order_orchestrator_handler = run
