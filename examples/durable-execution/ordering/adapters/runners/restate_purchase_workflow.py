from __future__ import annotations

import contextlib
import typing

import tesser.adapters as ts
import restate

import ordering.application.orchestrators as orchestrators
import ordering.application.relays as relays

_ALREADY_INVOKED: typing.Final[str] = "the workflow method was already invoked"


class RestateInvocationOrderOrchestratorRelay(ts.Runner):

    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        key = str(confirm_order_request.order.identity)
        self._restate_workflow_context.generic_send(
            "OrderOrchestrator",
            "confirm_order",
            relays.ConfirmOrderRequestSnapshot().serialize(confirm_order_request),
            key=key,
        )
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED, order_id=key
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        key = str(confirm_order_request.order.identity)
        try:
            return relays.ConfirmOrderResponseSnapshot().deserialize(
                await self._restate_workflow_context.generic_call(
                    "OrderOrchestrator",
                    "confirm_order",
                    relays.ConfirmOrderRequestSnapshot().serialize(confirm_order_request),
                    key=key,
                )
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


class RestateInvocationPurchaseActionsRelay(ts.Runner):

    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def run_take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        return relays.TakePaymentResponseSnapshot().deserialize(
            await self._restate_workflow_context.generic_call(
                "PurchaseActions",
                "take_payment",
                relays.TakePaymentRequestSnapshot().serialize(take_payment_request),
            )
        )


class RestatePurchaseWorkflow(ts.Runner):

    @contextlib.asynccontextmanager
    async def invocation(
        self, restate_workflow_context: restate.WorkflowContext
    ) -> typing.AsyncIterator[orchestrators.PurchaseOrchestrator]:
        yield orchestrators.PurchaseOrchestrator(
            RestateInvocationPurchaseActionsRelay(restate_workflow_context),
            RestateInvocationOrderOrchestratorRelay(restate_workflow_context),
        )
