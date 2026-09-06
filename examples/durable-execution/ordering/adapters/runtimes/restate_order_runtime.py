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
            return None
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
            return None
        return relays.OrderOrchestratorResponseSnapshot().deserialize(buf)


class RestatePrepareQuoteRequestSerde(ts.Serde, restate.serde.Serde[relays.PrepareQuoteRequest]):  # tesser:debt TB081

    def serialize(self, prepare_quote_request: relays.PrepareQuoteRequest | None) -> bytes:
        if prepare_quote_request is None:
            return b""
        return relays.PrepareQuoteRequestSnapshot().serialize(prepare_quote_request)

    def deserialize(self, buf: bytes) -> relays.PrepareQuoteRequest | None:
        if not buf:
            return None
        return relays.PrepareQuoteRequestSnapshot().deserialize(buf)


class RestatePrepareQuoteResponseSerde(  # tesser:debt TB081
    ts.Serde, restate.serde.Serde[relays.PrepareQuoteResponse]
):

    def serialize(self, prepare_quote_response: relays.PrepareQuoteResponse | None) -> bytes:
        if prepare_quote_response is None:
            return b""
        return relays.PrepareQuoteResponseSnapshot().serialize(prepare_quote_response)

    def deserialize(self, buf: bytes) -> relays.PrepareQuoteResponse | None:
        if not buf:
            return None
        return relays.PrepareQuoteResponseSnapshot().deserialize(buf)


class RestateOrderRuntime(ts.Job):

    def __init__(self, ordering_application_client: client.OrderingApplicationClient) -> None:
        self.order_actions_service = restate.Service("OrderActions")
        self.order_orchestrator_workflow = restate.Workflow("OrderOrchestrator")

        @self.order_actions_service.handler(
            input_serde=RestatePrepareQuoteRequestSerde(),
            output_serde=RestatePrepareQuoteResponseSerde(),
        )
        async def prepare_quote(  # tesser:debt TB023
            restate_context: restate.Context, prepare_quote_request: relays.PrepareQuoteRequest
        ) -> relays.PrepareQuoteResponse:
            try:
                return ordering_application_client.prepare_quote(prepare_quote_request)
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

        self.prepare_quote_handler = prepare_quote
        self.order_orchestrator_handler = run
