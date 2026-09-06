from __future__ import annotations

import tesser.application as ts

import ordering.application.ports as ports
import ordering.application.relays as relays
import ordering.domain as domain


class MapToGetProductPriceRequest(ts.Mapper, ports.GetProductPriceRequest):

    def __init__(self, sku: domain.Sku) -> None:
        super().__init__(sku=str(sku))


class MapToPrepareQuoteResponse(ts.Mapper, relays.PrepareQuoteResponse):

    def __init__(self, get_product_price_response: ports.GetProductPriceResponse) -> None:
        super().__init__(cents=get_product_price_response.cents)


class OrderActions(ts.Actions):

    def __init__(self, product_catalog_repository: ports.ProductCatalogRepository) -> None:
        self._product_catalog_repository = product_catalog_repository

    def prepare_quote(
        self, prepare_quote_request: relays.PrepareQuoteRequest
    ) -> relays.PrepareQuoteResponse:
        sku = domain.Sku(prepare_quote_request.sku)
        get_product_price_response = self._product_catalog_repository.get_product_price(
            MapToGetProductPriceRequest(sku)
        )
        return MapToPrepareQuoteResponse(get_product_price_response)
