from __future__ import annotations

import enum
import typing

import tesser.application as ts


class ChargePaymentMethodRequest(ts.Request):

    def __init__(self, order_id: str, cents: int, payment_method: str) -> None:
        self.order_id = order_id
        self.cents = cents
        self.payment_method = payment_method


class ChargePaymentMethodOutcome(enum.Enum):
    CHARGED = "charged"
    DECLINED = "declined"


class Receipt(ts.Response):

    def __init__(self, reference: str, cents: int) -> None:
        self.reference = reference
        self.cents = cents


class ChargePaymentMethodResponse(ts.Response):

    def __init__(
        self,
        outcome: ChargePaymentMethodOutcome,
        order_id: str,
        receipts: tuple[Receipt, ...],
        reasons: tuple[str, ...],
    ) -> None:
        self.outcome = outcome
        self.order_id = order_id
        self.receipts = receipts
        self.reasons = reasons


class PaymentProcessor(ts.Port, typing.Protocol):

    def charge_payment_method(
        self, charge_payment_method_request: ChargePaymentMethodRequest
    ) -> ChargePaymentMethodResponse: ...
