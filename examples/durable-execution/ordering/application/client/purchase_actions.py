from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays


class PurchaseApplicationClient(ts.Client, typing.Protocol):

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse: ...
