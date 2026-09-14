from __future__ import annotations

import enum
import typing

import tesser.application as ts


class GetProductPriceRequest(ts.Request):

    def __init__(self, sku: str) -> None:
        self.sku = sku


class GetProductPriceOutcome(enum.Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class Price(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class GetProductPriceResponse(ts.Response):

    def __init__(self, outcome: GetProductPriceOutcome, prices: tuple[Price, ...]) -> None:
        self.outcome = outcome
        self.prices = prices


class ProductCatalogRepository(ts.Port, typing.Protocol):

    def get_product_price(
        self, get_product_price_request: GetProductPriceRequest
    ) -> GetProductPriceResponse: ...
