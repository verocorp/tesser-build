from __future__ import annotations

import typing

import tesser.adapters as ts

import ordering.application.ports as ports

_PRICES: typing.Final[dict[str, int]] = {"widget": 250, "gadget": 1000}


class MapToGetProductPriceResponseFromPrice(ts.Mapper, ports.GetProductPriceResponse):

    def __init__(self, cents: int) -> None:
        super().__init__(
            outcome=ports.GetProductPriceOutcome.FOUND, prices=(ports.Price(cents=cents),)
        )


class MapToGetProductPriceResponseFromNothing(ts.Mapper, ports.GetProductPriceResponse):

    def __init__(self) -> None:
        super().__init__(outcome=ports.GetProductPriceOutcome.NOT_FOUND, prices=())


class MemoryProductCatalogRepository(ts.Repository):

    def __init__(self) -> None:
        self._prices = dict(_PRICES)

    def get_product_price(
        self, get_product_price_request: ports.GetProductPriceRequest
    ) -> ports.GetProductPriceResponse:
        cents = self._prices.get(get_product_price_request.sku)
        if cents is None:
            return MapToGetProductPriceResponseFromNothing()
        return MapToGetProductPriceResponseFromPrice(cents)

    def close(self) -> None:
        self._prices.clear()
