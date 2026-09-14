from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.ports as ports
import ordering.application.relays as relays
import ordering.domain as domain


class MapToGetProductPriceRequest(ts.Mapper, ports.GetProductPriceRequest):

    def __init__(self, sku: domain.Sku) -> None:
        super().__init__(sku=str(sku))


class MapToPriceProductResponse(ts.Mapper, relays.PriceProductResponse):

    def __init__(
        self,
        get_product_price_request: ports.GetProductPriceRequest,
        get_product_price_response: ports.GetProductPriceResponse,
    ) -> None:
        match get_product_price_response.outcome:
            case ports.GetProductPriceOutcome.FOUND:
                outcome = relays.PriceProductOutcome.PRICED
                prices: tuple[relays.Price, ...] = (
                    relays.Price(cents=get_product_price_response.prices[0].cents),
                )
                reasons: tuple[str, ...] = ()
            case ports.GetProductPriceOutcome.NOT_FOUND:
                outcome = relays.PriceProductOutcome.PRICE_NOT_FOUND
                prices = ()
                reasons = (f"no price for sku {get_product_price_request.sku!r}",)
            case _ as never:
                typing.assert_never(never)
        super().__init__(outcome=outcome, prices=prices, reasons=reasons)


class OrderActions(ts.Actions):

    def __init__(self, product_catalog_repository: ports.ProductCatalogRepository) -> None:
        self._product_catalog_repository = product_catalog_repository

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        get_product_price_request = MapToGetProductPriceRequest(
            domain.Sku(price_product_request.sku)
        )
        get_product_price_response = self._product_catalog_repository.get_product_price(
            get_product_price_request
        )
        return MapToPriceProductResponse(get_product_price_request, get_product_price_response)
