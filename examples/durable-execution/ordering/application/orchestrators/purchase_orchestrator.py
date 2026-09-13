from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays
import ordering.domain as domain


class MapToPurchaseSpec(ts.Mapper, domain.PurchaseSpec):

    def __init__(
        self, order: domain.Order, confirm_order_response: relays.ConfirmOrderResponse
    ) -> None:
        super().__init__(
            order_id=str(order.identity),
            priced_order_id=confirm_order_response.order_id,
            total_cents=confirm_order_response.confirmed_orders[0].total_cents,
        )


class MapToTakePaymentRequest(ts.Mapper, relays.TakePaymentRequest):

    def __init__(
        self, purchase: domain.Purchase, payment_method: domain.PaymentMethod
    ) -> None:
        super().__init__(
            order_id=str(purchase.identity),
            cents=int(purchase.total),
            payment_method=str(payment_method),
        )


class MapToPaymentSpec(ts.Mapper, domain.PaymentSpec):

    def __init__(self, take_payment_response: relays.TakePaymentResponse) -> None:
        super().__init__(
            order_id=take_payment_response.order_id,
            reference=take_payment_response.payments[0].reference,
            cents=take_payment_response.payments[0].cents,
        )


class MapToPayForOrderResponseFromPayment(ts.Mapper, relays.PayForOrderResponse):

    def __init__(self, purchase: domain.Purchase, payment: domain.Payment) -> None:
        super().__init__(
            outcome=relays.PayForOrderOutcome.PAID,
            order_id=str(purchase.identity),
            purchases=(
                relays.Purchase(
                    total_cents=int(purchase.total),
                    payment_reference=str(payment.reference),
                ),
            ),
            reasons=(),
        )


class MapToPayForOrderResponseFromConfirmOrderResponse(ts.Mapper, relays.PayForOrderResponse):

    def __init__(
        self, order: domain.Order, confirm_order_response: relays.ConfirmOrderResponse
    ) -> None:
        super().__init__(
            outcome=relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED,
            order_id=str(order.identity),
            purchases=(),
            reasons=confirm_order_response.reasons,
        )


class MapToPayForOrderResponseFromTakePaymentResponse(ts.Mapper, relays.PayForOrderResponse):

    def __init__(
        self, purchase: domain.Purchase, take_payment_response: relays.TakePaymentResponse
    ) -> None:
        super().__init__(
            outcome=relays.PayForOrderOutcome.PAYMENT_DECLINED,
            order_id=str(purchase.identity),
            purchases=(),
            reasons=take_payment_response.reasons,
        )


class PurchaseOrchestrator(ts.Orchestrator):

    def __init__(
        self,
        purchase_actions_runner: relays.PurchaseActionsRunner,
        order_orchestrator_runner: relays.OrderOrchestratorRunner,
    ) -> None:
        self._purchase_actions_runner = purchase_actions_runner
        self._order_orchestrator_runner = order_orchestrator_runner

    async def pay_for_order(
        self, pay_for_order_request: relays.PayForOrderRequest
    ) -> relays.PayForOrderResponse:
        order = pay_for_order_request.order
        confirm_order_response = await self._order_orchestrator_runner.run_confirm_order(
            relays.ConfirmOrderRequest(order=order)
        )
        match confirm_order_response.outcome:  # tesser:debt TB082
            case relays.ConfirmOrderOutcome.CONFIRMED:
                purchase = domain.Purchase(MapToPurchaseSpec(order, confirm_order_response))
            case (
                relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND
                | relays.ConfirmOrderOutcome.ALREADY_STARTED
            ):
                return MapToPayForOrderResponseFromConfirmOrderResponse(
                    order, confirm_order_response
                )
            case _ as never:
                typing.assert_never(never)
        payment_method = pay_for_order_request.payment_method
        take_payment_response = await self._purchase_actions_runner.run_take_payment(
            MapToTakePaymentRequest(purchase, payment_method)
        )
        match take_payment_response.outcome:  # tesser:debt TB082
            case relays.TakePaymentOutcome.TAKEN:
                payment = purchase.paid(MapToPaymentSpec(take_payment_response))
            case relays.TakePaymentOutcome.DECLINED:
                return MapToPayForOrderResponseFromTakePaymentResponse(
                    purchase, take_payment_response
                )
            case _ as never_taken:
                typing.assert_never(never_taken)
        return MapToPayForOrderResponseFromPayment(purchase, payment)
