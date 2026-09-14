from __future__ import annotations

import typing

import tesser.adapters as ts
import restate

import ordering.adapters.runtimes as runtimes
import ordering.application.relays as relays

_ALREADY_INVOKED: typing.Final[str] = "the workflow method was already invoked"


class RestateInvocationConfirmOrderRelay(ts.Runner):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_order_runtime: runtimes.RestateOrderRuntime,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_order_runtime = restate_order_runtime

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        key = str(confirm_order_request.order.identity)
        self._restate_workflow_context.workflow_send(
            self._restate_order_runtime.confirm_order_handler,
            key=key,
            arg=confirm_order_request,
        )
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED, order_id=key
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        key = str(confirm_order_request.order.identity)
        try:
            return await self._restate_workflow_context.workflow_call(
                self._restate_order_runtime.confirm_order_handler,
                key=key,
                arg=confirm_order_request,
            )
        except restate.TerminalError as terminal_error:
            if terminal_error.status_code == 409 and terminal_error.message == _ALREADY_INVOKED:
                return relays.ConfirmOrderResponse(
                    outcome=relays.ConfirmOrderOutcome.ALREADY_STARTED,
                    order_id=key,
                    confirmed_orders=(),
                    reasons=(),
                )
            raise
