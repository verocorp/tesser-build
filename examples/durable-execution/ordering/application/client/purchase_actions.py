from __future__ import annotations  # tesser:debt TB067

import typing

import tesser.application as ts

import ordering.application.relays as relays  # tesser:debt TB067


class PurchaseApplicationClient(ts.Client, typing.Protocol):

    def take_payment(  # tesser:debt TB081
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse: ...
