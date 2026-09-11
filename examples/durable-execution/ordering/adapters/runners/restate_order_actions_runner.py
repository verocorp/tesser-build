from __future__ import annotations

import tesser.adapters as ts
import restate

import ordering.adapters.runtimes as runtimes
import ordering.application.ports as ports
import ordering.application.relays as relays


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
                    raise ports.EngineRejected(terminal_error.message) from terminal_error
                case 404:
                    raise ports.EngineMissing(terminal_error.message) from terminal_error
                case 409:
                    raise ports.EngineConflict(terminal_error.message) from terminal_error
                case _:
                    raise
