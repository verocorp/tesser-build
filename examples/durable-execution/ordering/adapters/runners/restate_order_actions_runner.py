from __future__ import annotations

import tesser.adapters as ts
import restate

import ordering.adapters.runtimes as runtimes
import ordering.application.relays as relays
import tesser.errors as errors  # tesser:debt TB050


class RestateOrderActionsRunner(ts.Runner):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_order_runtime: runtimes.RestateOrderRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_order_runtime = restate_order_runtime

    async def run_price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        try:
            return await self._restate_workflow_context.service_call(
                self._restate_order_runtime.price_product_handler, price_product_request
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
            raise errors.DomainError(kind, "action_rejected", terminal_error.message) from terminal_error
