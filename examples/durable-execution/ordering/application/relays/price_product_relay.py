from __future__ import annotations

import enum  # tesser:debt TB062
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
            raise ValueError("a price product request is a sku")  # tesser:debt TB082
        return PriceProductRequest(sku=snapshot["sku"])


class PriceProductOutcome(enum.Enum):  # tesser:debt TB052
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
                "prices": [{"cents": price.cents} for price in price_product_response.prices],  # tesser:debt TB082
                "reasons": list(price_product_response.reasons),  # tesser:debt TB082
            }
        ).encode()

    def deserialize(self, buf: bytes) -> PriceProductResponse:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("prices"), list)
            and isinstance(snapshot.get("reasons"), list)
            and all(  # tesser:debt TB082
                isinstance(reason, str) and reason for reason in snapshot["reasons"]
            )
            and all(  # tesser:debt TB082
                isinstance(price, dict)
                and isinstance(price.get("cents"), int)
                and not isinstance(price.get("cents"), bool)
                and price["cents"] >= 0
                for price in snapshot["prices"]
            )
        ):
            raise ValueError(  # tesser:debt TB082
                "a price product response is an outcome, its prices, and its reasons"
            )
        try:  # tesser:debt TB082
            price_product_outcome = PriceProductOutcome(snapshot.get("outcome"))  # tesser:debt TB082 TB085
        except ValueError as value_error:
            raise ValueError("a price product response names a priced outcome") from value_error  # tesser:debt TB082
        return PriceProductResponse(
            outcome=price_product_outcome,
            prices=tuple(Price(cents=price["cents"]) for price in snapshot["prices"]),  # tesser:debt TB082
            reasons=tuple(snapshot["reasons"]),  # tesser:debt TB082
        )


class PriceProductRelay(ts.Relay, typing.Protocol):

    async def run_price_product(
        self, price_product_request: PriceProductRequest
    ) -> PriceProductResponse: ...
