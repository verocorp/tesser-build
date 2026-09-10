from __future__ import annotations

import json  # tesser:debt TB062
import typing

import tesser.application as ts

import tesser.errors as errors


class PriceProductRequest(ts.Request):  # tesser:debt TB052

    def __init__(self, sku: str) -> None:
        self.sku = sku


class PriceProductRequestSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, price_product_request: PriceProductRequest) -> bytes:
        return json.dumps({"sku": price_product_request.sku}).encode()

    def deserialize(self, buf: bytes) -> PriceProductRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("sku"), str)
            and snapshot["sku"]
        ):
            raise errors.invalid(
                "malformed_price_product_request_snapshot", "a price product request is a sku"
            )
        return PriceProductRequest(sku=snapshot["sku"])


class PriceProductResponse(ts.Response):  # tesser:debt TB052

    def __init__(self, cents: int) -> None:
        self.cents = cents


class PriceProductResponseSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, price_product_response: PriceProductResponse) -> bytes:
        return json.dumps({"cents": price_product_response.cents}).encode()

    def deserialize(self, buf: bytes) -> PriceProductResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("cents"), int)
            and not isinstance(snapshot.get("cents"), bool)
            and snapshot["cents"] >= 0
        ):
            raise errors.invalid(
                "malformed_price_product_response_snapshot",
                "a price product response is a price in cents",
            )
        return PriceProductResponse(cents=snapshot["cents"])


class OrderActionsRunner(ts.JobContext, typing.Protocol):  # tesser:debt TB052

    async def run_price_product(
        self, price_product_request: PriceProductRequest
    ) -> PriceProductResponse: ...
