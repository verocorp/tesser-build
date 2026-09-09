from __future__ import annotations

import tesser.application as ts

import ordering.application.ports as ports
import ordering.application.relays as relays
import ordering.domain as domain


class MapToGetProductPriceRequest(ts.Mapper, ports.GetProductPriceRequest):

    def __init__(self, sku: domain.Sku) -> None:
        super().__init__(sku=str(sku))


class MapToPriceSpec(ts.Mapper, domain.PriceSpec):

    def __init__(self, get_product_price_response: ports.GetProductPriceResponse) -> None:
        super().__init__(cents=get_product_price_response.cents)


class MapToPriceProductResponse(ts.Mapper, relays.PriceProductResponse):

    def __init__(self, price: domain.Price) -> None:
        super().__init__(cents=int(price))


class OrderActions(ts.Actions):

    def __init__(self, product_catalog_repository: ports.ProductCatalogRepository) -> None:
        self._product_catalog_repository = product_catalog_repository

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        sku = domain.Sku(price_product_request.sku)
        get_product_price_response = self._product_catalog_repository.get_product_price(
            MapToGetProductPriceRequest(sku)
        )
        price = domain.Price(MapToPriceSpec(get_product_price_response))
        return MapToPriceProductResponse(price)
