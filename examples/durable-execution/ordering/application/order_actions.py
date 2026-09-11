from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.ports as ports
import ordering.application.relays as relays
import ordering.domain as domain
import tesser.errors as errors


class MapToGetProductPriceRequest(ts.Mapper, ports.GetProductPriceRequest):

    def __init__(self, sku: domain.Sku) -> None:
        super().__init__(sku=str(sku))


class MapToPriceSpec(ts.Mapper, domain.PriceSpec):

    def __init__(
        self,
        get_product_price_request: ports.GetProductPriceRequest,
        get_product_price_response: ports.GetProductPriceResponse,
    ) -> None:
        match get_product_price_response.outcome:
            case ports.Priced.FOUND:
                record = get_product_price_response.prices[0]
            case ports.Priced.MISSING:
                raise ports.EngineMissing(
                    f"no price for sku {get_product_price_request.sku!r}"
                )
            case _ as never:
                typing.assert_never(never)
        super().__init__(cents=record.cents)


class MapToPriceProductResponse(ts.Mapper, relays.PriceProductResponse):

    def __init__(self, price: domain.Price) -> None:
        super().__init__(cents=int(price))


class OrderActions(ts.Actions):

    def __init__(self, product_catalog_repository: ports.ProductCatalogRepository) -> None:
        self._product_catalog_repository = product_catalog_repository

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        try:
            sku = domain.Sku(price_product_request.sku)
        except errors.DomainError as domain_error:
            raise ports.EngineRejected(domain_error.message) from domain_error
        get_product_price_request = MapToGetProductPriceRequest(sku)
        get_product_price_response = self._product_catalog_repository.get_product_price(
            get_product_price_request
        )
        try:
            price = domain.Price(
                MapToPriceSpec(get_product_price_request, get_product_price_response)
            )
        except errors.DomainError as domain_error:
            raise ports.EngineRejected(domain_error.message) from domain_error
        return MapToPriceProductResponse(price)
