from __future__ import annotations

import typing

import tesser.application as ts


class PriceRequest(ts.Request):

    def __init__(self, sku: str) -> None:
        self.sku = sku


class PriceResponse(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class CatalogRepository(ts.Port, typing.Protocol):

    async def price(self, request: PriceRequest) -> PriceResponse: ...
