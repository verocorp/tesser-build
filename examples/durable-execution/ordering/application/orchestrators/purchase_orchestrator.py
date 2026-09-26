from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays
import ordering.domain as domain

class MapToPurchaseSpec(ts.Mapper, domain.PurchaseSpec):

    def __init__(self, order: domain.Order) -> None:
        super().__init__(order_id=str(order.identity))


class MapToPurchaseConfirmationSpec(ts.Mapper, domain.PurchaseConfirmationSpec):

    def __init__(self, confirm_order_response: relays.ConfirmOrderResponse) -> None:
        super().__init__(
            order_id=confirm_order_response.order_id,
            totals=tuple(
                domain.PriceSpec(cents=confirmed_order.total_cents)
                for confirmed_order in confirm_order_response.confirmed_orders
            ),
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


class MapToPaymentResultSpec(ts.Mapper, domain.PaymentResultSpec):

    def __init__(self, take_payment_response: relays.TakePaymentResponse) -> None:
        super().__init__(
            outcome=take_payment_response.outcome.value,
            payments=tuple(
                domain.PaymentSpec(
                    order_id=take_payment_response.order_id,
                    reference=payment.reference,
                    cents=payment.cents,
                )
                for payment in take_payment_response.payments
            ),
        )


class MapToPayForOrderResponseFromPurchase(ts.Mapper, relays.PayForOrderResponse):

    def __init__(self, purchase: domain.Purchase) -> None:
        super().__init__(
            outcome=relays.PayForOrderOutcome.PAID,
            order_id=str(purchase.identity),
            purchases=(
                relays.Purchase(
                    total_cents=int(purchase.total),
                    payment_reference=str(purchase.payment.reference),
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
        purchase_actions_relay: relays.PurchaseActionsRelay,
        order_orchestrator_relay: relays.OrderOrchestratorRelay,
    ) -> None:
        self._purchase_actions_relay = purchase_actions_relay
        self._order_orchestrator_relay = order_orchestrator_relay

    async def pay_for_order(
        self, pay_for_order_request: relays.PayForOrderRequest
    ) -> relays.PayForOrderResponse:
        order = pay_for_order_request.order
        purchase = domain.Purchase(MapToPurchaseSpec(order))
        confirm_order_response = await self._order_orchestrator_relay.run_confirm_order(
            relays.ConfirmOrderRequest(order=order)
        )
        match purchase.confirm(MapToPurchaseConfirmationSpec(confirm_order_response)):
            case domain.PurchaseConfirmationOutcome.CONFIRMED:
                pass
            case domain.PurchaseConfirmationOutcome.ORDER_NOT_CONFIRMED:
                return MapToPayForOrderResponseFromConfirmOrderResponse(
                    order, confirm_order_response
                )
            case _ as never:
                typing.assert_never(never)
        payment_method = pay_for_order_request.payment_method
        take_payment_response = await self._purchase_actions_relay.run_take_payment(
            MapToTakePaymentRequest(purchase, payment_method)
        )
        match purchase.settle(MapToPaymentResultSpec(take_payment_response)):
            case domain.PurchaseSettlementOutcome.PAID:
                return MapToPayForOrderResponseFromPurchase(purchase)
            case domain.PurchaseSettlementOutcome.DECLINED:
                return MapToPayForOrderResponseFromTakePaymentResponse(
                    purchase, take_payment_response
                )
            case _ as never_taken:
                typing.assert_never(never_taken)
