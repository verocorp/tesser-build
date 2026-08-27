from __future__ import annotations

import typing

import tesser.adapters as ts

import ordering.application.ports.catalog_repository as catalog_repository
import tesser.errors as errors

_PRICES: typing.Final[dict[str, int]] = {"widget": 250, "gadget": 1000}


class MemoryCatalogRepository(ts.Repository):

    def __init__(self) -> None:
        self._prices = dict(_PRICES)

    async def price(self, request: catalog_repository.PriceRequest) -> catalog_repository.PriceResponse:
        cents = self._prices.get(request.sku)
        if cents is None:
            raise errors.not_found("unknown_sku", f"no price for sku {request.sku!r}")
        return catalog_repository.PriceResponse(cents=cents)

    def close(self) -> None:
        self._prices.clear()
