from __future__ import annotations  # tesser:debt TB067

import typing

import tesser.application as ts

import ordering.application.relays as relays  # tesser:debt TB067


class OrderingApplicationClient(ts.Client, typing.Protocol):

    def price_product(  # tesser:debt TB081
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse: ...
