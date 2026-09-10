from __future__ import annotations

import tesser.application as ts

import ordering.application.ports as ports
import ordering.application.relays as relays
import ordering.domain as domain


class MapToChargeRequest(ts.Mapper, ports.ChargeRequest):

    def __init__(self, order_id: domain.OrderId, price: domain.Price) -> None:
        super().__init__(order_id=str(order_id), cents=int(price))


class MapToTakePaymentResponse(ts.Mapper, relays.TakePaymentResponse):

    def __init__(self, charge_response: ports.ChargeResponse) -> None:
        super().__init__(
            order_id=charge_response.order_id,
            reference=charge_response.reference,
            cents=charge_response.cents,
        )


class PurchaseActions(ts.Actions):

    def __init__(self, payment_processor: ports.PaymentProcessor) -> None:
        self._payment_processor = payment_processor

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        order_id = domain.OrderId(take_payment_request.order_id)
        price = domain.Price(domain.PriceSpec(cents=take_payment_request.cents))
        charge_response = self._payment_processor.charge(MapToChargeRequest(order_id, price))
        return MapToTakePaymentResponse(charge_response)
