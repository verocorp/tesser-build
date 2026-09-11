from __future__ import annotations

import json
import typing

import tesser.application as ts

import ordering.application.ports as ports


class PriceProductRequest(ts.Request):

    def __init__(self, sku: str) -> None:
        self.sku = sku


class PriceProductRequestSnapshot(ts.Serde):

    def serialize(self, price_product_request: PriceProductRequest) -> bytes:
        return json.dumps({"sku": price_product_request.sku}).encode()

    def deserialize(self, buf: bytes) -> PriceProductRequest:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("sku"), str)
            and snapshot["sku"]
        ):
            raise ports.EngineRejected("a price product request is a sku")  # tesser:debt TB082
        return PriceProductRequest(sku=snapshot["sku"])


class PriceProductResponse(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class PriceProductResponseSnapshot(ts.Serde):

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
            raise ports.EngineRejected("a price product response is a price in cents")  # tesser:debt TB082
        return PriceProductResponse(cents=snapshot["cents"])


class OrderActionsRunner(ts.Relay, typing.Protocol):

    async def run_price_product(
        self, price_product_request: PriceProductRequest
    ) -> PriceProductResponse: ...
