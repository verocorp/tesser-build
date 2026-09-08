from __future__ import annotations

import json  # tesser:debt TB062
import typing

import tesser.application as ts


class PriceProductRequest(ts.Request):  # tesser:debt TB052

    def __init__(self, sku: str) -> None:
        self.sku = sku


class PriceProductRequestSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, price_product_request: PriceProductRequest) -> bytes:
        return json.dumps({"sku": price_product_request.sku}).encode()

    def deserialize(self, buf: bytes) -> PriceProductRequest:
        return PriceProductRequest(sku=json.loads(buf)["sku"])


class PriceProductResponse(ts.Response):  # tesser:debt TB052

    def __init__(self, cents: int) -> None:
        self.cents = cents


class PriceProductResponseSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, price_product_response: PriceProductResponse) -> bytes:
        return json.dumps({"cents": price_product_response.cents}).encode()

    def deserialize(self, buf: bytes) -> PriceProductResponse:
        return PriceProductResponse(cents=json.loads(buf)["cents"])


class OrderActionsRunner(ts.JobContext, typing.Protocol):  # tesser:debt TB052

    async def run_price_product(
        self, price_product_request: PriceProductRequest
    ) -> PriceProductResponse: ...
