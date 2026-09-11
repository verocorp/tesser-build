from __future__ import annotations

import typing

import tesser.adapters as ts

import ordering.application.ports as ports

_PRICES: typing.Final[dict[str, int]] = {"widget": 250, "gadget": 1000}


class MemoryProductCatalogRepository(ts.Repository):

    def __init__(self) -> None:
        self._prices = dict(_PRICES)

    def get_product_price(
        self, get_product_price_request: ports.GetProductPriceRequest
    ) -> ports.GetProductPriceResponse:
        cents = self._prices.get(get_product_price_request.sku)
        if cents is None:
            return ports.GetProductPriceResponse(outcome=ports.Priced.MISSING, prices=())
        return ports.GetProductPriceResponse(
            outcome=ports.Priced.FOUND, prices=(ports.PriceRecord(cents=cents),)
        )

    def close(self) -> None:
        self._prices.clear()
