from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import ordering.adapters.runners as runners
import ordering.application.client as client
import ordering.application.orchestrators as orchestrators
import ordering.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"
_RETRY_POLICY: typing.Final[restate.InvocationRetryPolicy] = restate.InvocationRetryPolicy(
    max_attempts=5, on_max_attempts="pause"
)


class RestateConfirmOrderRequestSerde(ts.Serde, restate_serde.Serde[relays.ConfirmOrderRequest]):

    def serialize(self, confirm_order_request: relays.ConfirmOrderRequest | None) -> bytes:
        if confirm_order_request is None:
            return b""
        return relays.ConfirmOrderRequestSnapshot().serialize(confirm_order_request)

    def deserialize(self, buf: bytes) -> relays.ConfirmOrderRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        try:  # tesser:debt TB082
            return relays.ConfirmOrderRequestSnapshot().deserialize(buf)
        except ValueError as value_error:
            raise restate.TerminalError(str(value_error), status_code=400) from value_error


class RestateConfirmOrderResponseSerde(ts.Serde, restate_serde.Serde[relays.ConfirmOrderResponse]):

    def serialize(self, confirm_order_response: relays.ConfirmOrderResponse | None) -> bytes:
        if confirm_order_response is None:
            return b""
        return relays.ConfirmOrderResponseSnapshot().serialize(confirm_order_response)

    def deserialize(self, buf: bytes) -> relays.ConfirmOrderResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        try:  # tesser:debt TB082
            return relays.ConfirmOrderResponseSnapshot().deserialize(buf)
        except ValueError as value_error:
            raise restate.TerminalError(str(value_error), status_code=400) from value_error


class RestatePriceProductRequestSerde(ts.Serde, restate_serde.Serde[relays.PriceProductRequest]):

    def serialize(self, price_product_request: relays.PriceProductRequest | None) -> bytes:
        if price_product_request is None:
            return b""
        return relays.PriceProductRequestSnapshot().serialize(price_product_request)

    def deserialize(self, buf: bytes) -> relays.PriceProductRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        try:  # tesser:debt TB082
            return relays.PriceProductRequestSnapshot().deserialize(buf)
        except ValueError as value_error:
            raise restate.TerminalError(str(value_error), status_code=400) from value_error


class RestatePriceProductResponseSerde(ts.Serde, restate_serde.Serde[relays.PriceProductResponse]):

    def serialize(self, price_product_response: relays.PriceProductResponse | None) -> bytes:
        if price_product_response is None:
            return b""
        return relays.PriceProductResponseSnapshot().serialize(price_product_response)

    def deserialize(self, buf: bytes) -> relays.PriceProductResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        try:  # tesser:debt TB082
            return relays.PriceProductResponseSnapshot().deserialize(buf)
        except ValueError as value_error:
            raise restate.TerminalError(str(value_error), status_code=400) from value_error


class RestatePayForOrderRequestSerde(ts.Serde, restate_serde.Serde[relays.PayForOrderRequest]):

    def serialize(self, pay_for_order_request: relays.PayForOrderRequest | None) -> bytes:
        if pay_for_order_request is None:
            return b""
        return relays.PayForOrderRequestSnapshot().serialize(pay_for_order_request)

    def deserialize(self, buf: bytes) -> relays.PayForOrderRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        try:  # tesser:debt TB082
            return relays.PayForOrderRequestSnapshot().deserialize(buf)
        except ValueError as value_error:
            raise restate.TerminalError(str(value_error), status_code=400) from value_error


class RestatePayForOrderResponseSerde(ts.Serde, restate_serde.Serde[relays.PayForOrderResponse]):

    def serialize(self, pay_for_order_response: relays.PayForOrderResponse | None) -> bytes:
        if pay_for_order_response is None:
            return b""
        return relays.PayForOrderResponseSnapshot().serialize(pay_for_order_response)

    def deserialize(self, buf: bytes) -> relays.PayForOrderResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        try:  # tesser:debt TB082
            return relays.PayForOrderResponseSnapshot().deserialize(buf)
        except ValueError as value_error:
            raise restate.TerminalError(str(value_error), status_code=400) from value_error


class RestateTakePaymentRequestSerde(ts.Serde, restate_serde.Serde[relays.TakePaymentRequest]):

    def serialize(self, take_payment_request: relays.TakePaymentRequest | None) -> bytes:
        if take_payment_request is None:
            return b""
        return relays.TakePaymentRequestSnapshot().serialize(take_payment_request)

    def deserialize(self, buf: bytes) -> relays.TakePaymentRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        try:  # tesser:debt TB082
            return relays.TakePaymentRequestSnapshot().deserialize(buf)
        except ValueError as value_error:
            raise restate.TerminalError(str(value_error), status_code=400) from value_error


class RestateTakePaymentResponseSerde(ts.Serde, restate_serde.Serde[relays.TakePaymentResponse]):

    def serialize(self, take_payment_response: relays.TakePaymentResponse | None) -> bytes:
        if take_payment_response is None:
            return b""
        return relays.TakePaymentResponseSnapshot().serialize(take_payment_response)

    def deserialize(self, buf: bytes) -> relays.TakePaymentResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        try:  # tesser:debt TB082
            return relays.TakePaymentResponseSnapshot().deserialize(buf)
        except ValueError as value_error:
            raise restate.TerminalError(str(value_error), status_code=400) from value_error


class RestateOrderRuntime(ts.Runtime):

    def __init__(
        self,
        ordering_application_client: client.OrderingApplicationClient,
        purchase_application_client: client.PurchaseApplicationClient,
    ) -> None:
        self.order_actions_service = restate.Service(
            "OrderActions", invocation_retry_policy=_RETRY_POLICY
        )
        self.order_orchestrator_workflow = restate.Workflow(
            "OrderOrchestrator", invocation_retry_policy=_RETRY_POLICY
        )
        self.purchase_actions_service = restate.Service(
            "PurchaseActions", invocation_retry_policy=_RETRY_POLICY
        )
        self.purchase_orchestrator_workflow = restate.Workflow(
            "PurchaseOrchestrator", invocation_retry_policy=_RETRY_POLICY
        )

        @self.order_actions_service.handler(
            input_serde=RestatePriceProductRequestSerde(),
            output_serde=RestatePriceProductResponseSerde(),
        )
        async def price_product(  # tesser:debt TB023
            restate_context: restate.Context, price_product_request: relays.PriceProductRequest
        ) -> relays.PriceProductResponse:
            return ordering_application_client.price_product(price_product_request)

        @self.order_orchestrator_workflow.main(
            input_serde=RestateConfirmOrderRequestSerde(),
            output_serde=RestateConfirmOrderResponseSerde(),
        )
        async def confirm_order(  # tesser:debt TB023
            restate_workflow_context: restate.WorkflowContext,
            confirm_order_request: relays.ConfirmOrderRequest,
        ) -> relays.ConfirmOrderResponse:
            return await orchestrators.OrderOrchestrator(
                runners.RestateOrderActionsRunner(restate_workflow_context, self)
            ).confirm_order(confirm_order_request)

        @self.purchase_actions_service.handler(
            input_serde=RestateTakePaymentRequestSerde(),
            output_serde=RestateTakePaymentResponseSerde(),
        )
        async def take_payment(  # tesser:debt TB023
            restate_context: restate.Context, take_payment_request: relays.TakePaymentRequest
        ) -> relays.TakePaymentResponse:
            return purchase_application_client.take_payment(take_payment_request)

        @self.purchase_orchestrator_workflow.main(
            input_serde=RestatePayForOrderRequestSerde(),
            output_serde=RestatePayForOrderResponseSerde(),
        )
        async def pay_for_order(  # tesser:debt TB023
            restate_workflow_context: restate.WorkflowContext,
            pay_for_order_request: relays.PayForOrderRequest,
        ) -> relays.PayForOrderResponse:
            return await orchestrators.PurchaseOrchestrator(
                runners.RestatePurchaseActionsRunner(restate_workflow_context, self),
                runners.RestateOrderOrchestratorChildRunner(restate_workflow_context, self),
            ).pay_for_order(pay_for_order_request)

        self.price_product_handler = price_product
        self.confirm_order_handler = confirm_order
        self.take_payment_handler = take_payment
        self.pay_for_order_handler = pay_for_order
