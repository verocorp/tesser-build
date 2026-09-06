from __future__ import annotations  # tesser:debt TB041

import tesser.adapters as ts
import restate

import ordering.adapters.runtimes as runtimes
import ordering.application.relays as relays  # tesser:debt TB060
import tesser.errors as errors


class RestateOrderActionsRunner(ts.JobContext):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_order_runtime: runtimes.RestateOrderRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_order_runtime = restate_order_runtime

    async def run_prepare_quote(
        self, prepare_quote_request: relays.PrepareQuoteRequest
    ) -> relays.PrepareQuoteResponse:
        try:
            return await self._restate_workflow_context.service_call(
                self._restate_order_runtime.prepare_quote_handler, prepare_quote_request
            )
        except restate.TerminalError as terminal_error:
            raise errors.DomainError(
                errors.Kind.NOT_FOUND, "action_rejected", terminal_error.message
            ) from terminal_error
