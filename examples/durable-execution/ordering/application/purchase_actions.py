from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.ports as ports
import ordering.application.relays as relays
import ordering.domain as domain


class MapToChargePaymentMethodRequest(ts.Mapper, ports.ChargePaymentMethodRequest):

    def __init__(
        self,
        order_id: domain.OrderId,
        price: domain.Price,
        payment_method: domain.PaymentMethod,
    ) -> None:
        super().__init__(
            order_id=str(order_id), cents=int(price), payment_method=str(payment_method)
        )


class MapToTakePaymentResponse(ts.Mapper, relays.TakePaymentResponse):

    def __init__(
        self, charge_payment_method_response: ports.ChargePaymentMethodResponse
    ) -> None:
        match charge_payment_method_response.outcome:
            case ports.ChargePaymentMethodOutcome.CHARGED:
                outcome = relays.TakePaymentOutcome.TAKEN
                payments: tuple[relays.Payment, ...] = (
                    relays.Payment(
                        reference=charge_payment_method_response.receipts[0].reference,
                        cents=charge_payment_method_response.receipts[0].cents,
                    ),
                )
                reasons: tuple[str, ...] = ()
            case ports.ChargePaymentMethodOutcome.DECLINED:
                outcome = relays.TakePaymentOutcome.DECLINED
                payments = ()
                reasons = charge_payment_method_response.reasons
            case _ as never:
                typing.assert_never(never)
        super().__init__(
            outcome=outcome,
            order_id=charge_payment_method_response.order_id,
            payments=payments,
            reasons=reasons,
        )


class PurchaseActions(ts.Actions):

    def __init__(self, payment_processor: ports.PaymentProcessor) -> None:
        self._payment_processor = payment_processor

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        order_id = domain.OrderId(take_payment_request.order_id)
        price = domain.Price(domain.PriceSpec(cents=take_payment_request.cents))
        payment_method = domain.PaymentMethod(take_payment_request.payment_method)
        charge_payment_method_response = self._payment_processor.charge_payment_method(
            MapToChargePaymentMethodRequest(order_id, price, payment_method)
        )
        return MapToTakePaymentResponse(charge_payment_method_response)
