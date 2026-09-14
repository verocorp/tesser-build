from __future__ import annotations

import typing

import tesser.adapters as ts

import ordering.application.ports as ports

_DECLINED_PAYMENT_METHOD: typing.Final[str] = "declined"


class MapToReceipt(ts.Mapper, ports.Receipt):

    def __init__(
        self, charge_payment_method_request: ports.ChargePaymentMethodRequest
    ) -> None:
        super().__init__(
            reference=f"pay-{charge_payment_method_request.order_id}",
            cents=charge_payment_method_request.cents,
        )


class MapToChargePaymentMethodResponseFromReceipt(ts.Mapper, ports.ChargePaymentMethodResponse):

    def __init__(self, order_id: str, receipt: ports.Receipt) -> None:
        super().__init__(
            outcome=ports.ChargePaymentMethodOutcome.CHARGED,
            order_id=order_id,
            receipts=(receipt,),
            reasons=(),
        )


class MapToChargePaymentMethodResponseFromRefusal(ts.Mapper, ports.ChargePaymentMethodResponse):

    def __init__(self, order_id: str) -> None:
        super().__init__(
            outcome=ports.ChargePaymentMethodOutcome.DECLINED,
            order_id=order_id,
            receipts=(),
            reasons=(f"the processor declined the charge for order {order_id!r}",),
        )


class MemoryPaymentProcessor(ts.Gateway):

    def __init__(self) -> None:
        self._receipts: dict[str, ports.Receipt] = {}

    def charge_payment_method(
        self, charge_payment_method_request: ports.ChargePaymentMethodRequest
    ) -> ports.ChargePaymentMethodResponse:
        if charge_payment_method_request.payment_method == _DECLINED_PAYMENT_METHOD:
            return MapToChargePaymentMethodResponseFromRefusal(charge_payment_method_request.order_id)
        return MapToChargePaymentMethodResponseFromReceipt(
            charge_payment_method_request.order_id,
            self._receipts.setdefault(
                charge_payment_method_request.order_id,
                MapToReceipt(charge_payment_method_request),
            ),
        )

    def close(self) -> None:
        self._receipts.clear()
