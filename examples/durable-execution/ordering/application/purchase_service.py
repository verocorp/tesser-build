from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays
import ordering.client as client
import ordering.domain as domain
import tesser.errors as errors

_ALREADY_STARTED: typing.Final[str] = "the order was already started"


class MapToOrderSpec(ts.Mapper, domain.OrderSpec):

    def __init__(self, make_order_payment_request: client.MakeOrderPaymentRequest) -> None:
        super().__init__(
            order_id=make_order_payment_request.order_id,
            sku=make_order_payment_request.sku,
            quantity=make_order_payment_request.quantity,
        )


class MapToMakeOrderPaymentResponse(ts.Mapper, client.MakeOrderPaymentResponse):

    def __init__(self, pay_for_order_response: relays.PayForOrderResponse) -> None:
        super().__init__(
            order_id=pay_for_order_response.order_id,
            total_cents=pay_for_order_response.purchases[0].total_cents,
            payment_reference=pay_for_order_response.purchases[0].payment_reference,
        )


class PurchaseService(ts.ApplicationService):

    def __init__(
        self, pay_for_order_relay: relays.PayForOrderRelay
    ) -> None:
        self._pay_for_order_relay = pay_for_order_relay

    async def make_order_payment(
        self, make_order_payment_request: client.MakeOrderPaymentRequest
    ) -> client.MakeOrderPaymentResponse:
        try:
            order = domain.Order(MapToOrderSpec(make_order_payment_request))
            payment_method = domain.PaymentMethod(make_order_payment_request.payment_method)
        except errors.DomainError as domain_error:
            raise client.OrderRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        pay_for_order_response = await self._pay_for_order_relay.run_pay_for_order(
            relays.PayForOrderRequest(order=order, payment_method=payment_method)
        )
        match pay_for_order_response.outcome:  # tesser:debt TB082
            case relays.PayForOrderOutcome.PAID:
                return MapToMakeOrderPaymentResponse(pay_for_order_response)
            case relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED:
                raise client.OrderNotConfirmed(pay_for_order_response.reasons[0])
            case relays.PayForOrderOutcome.PAYMENT_DECLINED:
                raise client.PaymentDeclined(pay_for_order_response.reasons[0])
            case relays.PayForOrderOutcome.ALREADY_STARTED:
                raise client.OrderAlreadyStarted(_ALREADY_STARTED)
            case _ as never:
                typing.assert_never(never)
