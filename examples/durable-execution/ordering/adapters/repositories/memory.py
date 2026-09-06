from __future__ import annotations

import typing

import tesser.adapters as ts

import ordering.application.ports as ports
import tesser.errors as errors

_PRICES: typing.Final[dict[str, int]] = {"widget": 250, "gadget": 1000}


class MemoryCatalogRepository(ts.Repository):

    def __init__(self) -> None:
        self._prices = dict(_PRICES)

    def price(self, price_request: ports.PriceRequest) -> ports.PriceResponse:
        cents = self._prices.get(price_request.sku)
        if cents is None:
            raise errors.not_found("unknown_sku", f"no price for sku {price_request.sku!r}")
        return ports.PriceResponse(cents=cents)

    def close(self) -> None:
        self._prices.clear()
