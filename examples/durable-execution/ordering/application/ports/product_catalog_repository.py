from __future__ import annotations

import enum
import typing

import tesser.application as ts


class GetProductPriceRequest(ts.Request):

    def __init__(self, sku: str) -> None:
        self.sku = sku


class Priced(enum.Enum):
    FOUND = "found"
    MISSING = "missing"


class PriceRecord(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class GetProductPriceResponse(ts.Response):

    def __init__(self, outcome: Priced, prices: tuple[PriceRecord, ...]) -> None:
        self.outcome = outcome
        self.prices = prices


class ProductCatalogRepository(ts.Port, typing.Protocol):

    def get_product_price(
        self, get_product_price_request: GetProductPriceRequest
    ) -> GetProductPriceResponse: ...
