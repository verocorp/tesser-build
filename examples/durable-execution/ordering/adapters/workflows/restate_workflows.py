from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import ordering.adapters.activities as activities
import ordering.application.orchestrators as orchestrators
import ordering.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"
_ALREADY_INVOKED: typing.Final[str] = "the workflow method was already invoked"
_FOREIGN_ORDER: typing.Final[str] = "a request names the order its workflow is keyed by"


class RestateConfirmOrderRequestSerde(ts.Serde, restate_serde.Serde[relays.ConfirmOrderRequest]):

    def serialize(self, confirm_order_request: relays.ConfirmOrderRequest | None) -> bytes:
        if confirm_order_request is None:
            return b""
        return relays.ConfirmOrderRequestSnapshot().serialize(confirm_order_request)

    def deserialize(self, buf: bytes) -> relays.ConfirmOrderRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.ConfirmOrderRequestSnapshot().deserialize(buf)


class RestateConfirmOrderResponseSerde(ts.Serde, restate_serde.Serde[relays.ConfirmOrderResponse]):

    def serialize(self, confirm_order_response: relays.ConfirmOrderResponse | None) -> bytes:
        if confirm_order_response is None:
            return b""
        return relays.ConfirmOrderResponseSnapshot().serialize(confirm_order_response)

    def deserialize(self, buf: bytes) -> relays.ConfirmOrderResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.ConfirmOrderResponseSnapshot().deserialize(buf)


class RestatePayForOrderRequestSerde(ts.Serde, restate_serde.Serde[relays.PayForOrderRequest]):

    def serialize(self, pay_for_order_request: relays.PayForOrderRequest | None) -> bytes:
        if pay_for_order_request is None:
            return b""
        return relays.PayForOrderRequestSnapshot().serialize(pay_for_order_request)

    def deserialize(self, buf: bytes) -> relays.PayForOrderRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PayForOrderRequestSnapshot().deserialize(buf)


class RestatePayForOrderResponseSerde(ts.Serde, restate_serde.Serde[relays.PayForOrderResponse]):

    def serialize(self, pay_for_order_response: relays.PayForOrderResponse | None) -> bytes:
        if pay_for_order_response is None:
            return b""
        return relays.PayForOrderResponseSnapshot().serialize(pay_for_order_response)

    def deserialize(self, buf: bytes) -> relays.PayForOrderResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.PayForOrderResponseSnapshot().deserialize(buf)


class RestateInvocationOrderActionsRelay(ts.Dispatcher):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_price_product: activities.RestatePriceProduct,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_price_product = restate_price_product

    async def run_price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return await self._restate_workflow_context.service_call(
            self._restate_price_product.handler, price_product_request
        )


class RestateConfirmOrder(ts.Workflow):

    def __init__(
        self,
        order_orchestrator_workflow: restate.Workflow,
        restate_price_product: activities.RestatePriceProduct,
    ) -> None:
        @order_orchestrator_workflow.main(
            input_serde=RestateConfirmOrderRequestSerde(),
            output_serde=RestateConfirmOrderResponseSerde(),
        )
        async def confirm_order(
            restate_workflow_context: restate.WorkflowContext,
            confirm_order_request: relays.ConfirmOrderRequest,
        ) -> relays.ConfirmOrderResponse:
            if str(confirm_order_request.order.identity) != restate_workflow_context.key():
                raise restate.TerminalError(_FOREIGN_ORDER, status_code=400)
            return await orchestrators.OrderOrchestrator(
                RestateInvocationOrderActionsRelay(restate_workflow_context, restate_price_product)
            ).confirm_order(confirm_order_request)

        self.handler = confirm_order


class RestateInvocationPurchaseActionsRelay(ts.Dispatcher):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_take_payment: activities.RestateTakePayment,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_take_payment = restate_take_payment

    async def run_take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        return await self._restate_workflow_context.service_call(
            self._restate_take_payment.handler, take_payment_request
        )


class RestateInvocationOrderOrchestratorRelay(ts.Dispatcher):

    def __init__(
        self,
        restate_workflow_context: restate.WorkflowContext,
        restate_confirm_order: RestateConfirmOrder,
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_confirm_order = restate_confirm_order

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        key = str(confirm_order_request.order.identity)
        self._restate_workflow_context.workflow_send(
            self._restate_confirm_order.handler, key=key, arg=confirm_order_request
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
                self._restate_confirm_order.handler, key=key, arg=confirm_order_request
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


class RestatePayForOrder(ts.Workflow):

    def __init__(
        self,
        purchase_orchestrator_workflow: restate.Workflow,
        restate_take_payment: activities.RestateTakePayment,
        restate_confirm_order: RestateConfirmOrder,
    ) -> None:
        @purchase_orchestrator_workflow.main(
            input_serde=RestatePayForOrderRequestSerde(),
            output_serde=RestatePayForOrderResponseSerde(),
        )
        async def pay_for_order(
            restate_workflow_context: restate.WorkflowContext,
            pay_for_order_request: relays.PayForOrderRequest,
        ) -> relays.PayForOrderResponse:
            if str(pay_for_order_request.order.identity) != restate_workflow_context.key():
                raise restate.TerminalError(_FOREIGN_ORDER, status_code=400)
            return await orchestrators.PurchaseOrchestrator(
                RestateInvocationPurchaseActionsRelay(restate_workflow_context, restate_take_payment),
                RestateInvocationOrderOrchestratorRelay(restate_workflow_context, restate_confirm_order),
            ).pay_for_order(pay_for_order_request)

        self.handler = pay_for_order
