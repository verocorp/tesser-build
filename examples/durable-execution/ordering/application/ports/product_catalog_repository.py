from __future__ import annotations

import typing

import tesser.application as ts


class GetProductPriceRequest(ts.Request):

    def __init__(self, sku: str) -> None:
        self.sku = sku


class GetProductPriceResponse(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class ProductCatalogRepository(ts.Port, typing.Protocol):

    def get_product_price(
        self, get_product_price_request: GetProductPriceRequest
    ) -> GetProductPriceResponse: ...
