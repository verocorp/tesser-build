from __future__ import annotations

import tesser.adapters as ts
import restate

import ordering.adapters.runtimes as runtimes
import ordering.application.ports as ports  # tesser:debt TB060
import ordering.application.relays as relays


class RestatePurchaseActionsRunner(ts.Runner):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_order_runtime: runtimes.RestateOrderRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_order_runtime = restate_order_runtime

    async def run_take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        try:
            return await self._restate_workflow_context.service_call(
                self._restate_order_runtime.take_payment_handler, take_payment_request
            )
        except restate.TerminalError as terminal_error:
            match terminal_error.status_code:
                case 422:
                    raise ports.EngineRejected(terminal_error.message) from terminal_error
                case 404:
                    raise ports.EngineMissing(terminal_error.message) from terminal_error
                case 409:
                    raise ports.EngineConflict(terminal_error.message) from terminal_error
                case _:
                    raise
