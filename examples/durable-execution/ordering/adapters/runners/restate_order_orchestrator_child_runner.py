from __future__ import annotations

import tesser.adapters as ts
import restate

import ordering.adapters.runtimes as runtimes
import ordering.application.relays as relays
import tesser.errors as errors


class RestateOrderOrchestratorChildRunner(ts.Runner):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_order_runtime: runtimes.RestateOrderRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_order_runtime = restate_order_runtime

    async def start_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.StartOrderOrchestratorResponse:
        key = str(order_orchestrator_request.order.identity)
        self._restate_workflow_context.workflow_send(
            self._restate_order_runtime.order_orchestrator_handler,
            key=key,
            arg=order_orchestrator_request,
        )
        return relays.StartOrderOrchestratorResponse(order_id=key)

    async def run_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.OrderOrchestratorResponse:
        try:
            return await self._restate_workflow_context.workflow_call(
                self._restate_order_runtime.order_orchestrator_handler,
                key=str(order_orchestrator_request.order.identity),
                arg=order_orchestrator_request,
            )
        except restate.TerminalError as terminal_error:
            match terminal_error.status_code:
                case 422:
                    kind = errors.Kind.VALIDATION
                case 404:
                    kind = errors.Kind.NOT_FOUND
                case 409:
                    kind = errors.Kind.CONFLICT
                case _:
                    raise
            raise errors.DomainError(kind, "order_rejected", terminal_error.message) from terminal_error
