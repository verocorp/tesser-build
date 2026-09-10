from __future__ import annotations

import typing

import tesser.application as ts


class ChargeRequest(ts.Request):

    def __init__(self, order_id: str, cents: int) -> None:
        self.order_id = order_id
        self.cents = cents


class ChargeResponse(ts.Response):

    def __init__(self, order_id: str, reference: str, cents: int) -> None:
        self.order_id = order_id
        self.reference = reference
        self.cents = cents


class PaymentProcessor(ts.Port, typing.Protocol):

    def charge(self, charge_request: ChargeRequest) -> ChargeResponse: ...
