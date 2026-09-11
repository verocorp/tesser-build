from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays


class OrderingApplicationClient(ts.Client, typing.Protocol):

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse: ...
