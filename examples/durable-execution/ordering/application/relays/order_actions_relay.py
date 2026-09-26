from __future__ import annotations

import enum
import json
import typing

import tesser.application as ts


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
            raise ValueError("a price product request is a sku")
        return PriceProductRequest(sku=snapshot["sku"])


class PriceProductOutcome(enum.Enum):
    PRICED = "priced"
    PRICE_NOT_FOUND = "price_not_found"


class Price(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class PriceProductResponse(ts.Response):

    def __init__(
        self,
        outcome: PriceProductOutcome,
        prices: tuple[Price, ...],
        reasons: tuple[str, ...],
    ) -> None:
        self.outcome = outcome
        self.prices = prices
        self.reasons = reasons


class PriceProductResponseSnapshot(ts.Serde):

    def serialize(self, price_product_response: PriceProductResponse) -> bytes:
        return json.dumps(
            {
                "outcome": price_product_response.outcome.value,
                "prices": [{"cents": price.cents} for price in price_product_response.prices],
                "reasons": list(price_product_response.reasons),
            }
        ).encode()

    def deserialize(self, buf: bytes) -> PriceProductResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("prices"), list)
            and isinstance(snapshot.get("reasons"), list)
            and all(
                isinstance(reason, str) and reason for reason in snapshot["reasons"]
            )
            and all(
                isinstance(price, dict)
                and isinstance(price.get("cents"), int)
                and not isinstance(price.get("cents"), bool)
                and price["cents"] >= 0
                for price in snapshot["prices"]
            )
        ):
            raise ValueError(
                "a price product response is an outcome, its prices, and its reasons"
            )
        try:
            price_product_outcome = PriceProductOutcome(snapshot.get("outcome"))
        except ValueError as value_error:
            raise ValueError("a price product response names a priced outcome") from value_error
        return PriceProductResponse(
            outcome=price_product_outcome,
            prices=tuple(Price(cents=price["cents"]) for price in snapshot["prices"]),
            reasons=tuple(snapshot["reasons"]),
        )


class OrderActionsRelay(ts.Relay, typing.Protocol):

    async def run_price_product(
        self, price_product_request: PriceProductRequest
    ) -> PriceProductResponse: ...
