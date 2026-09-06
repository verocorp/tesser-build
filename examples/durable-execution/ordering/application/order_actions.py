from __future__ import annotations

import tesser.application as ts

import ordering.application.ports as ports
import ordering.domain as domain


class MapToPriceRequest(ts.Mapper, ports.PriceRequest):

    def __init__(self, sku: domain.Sku) -> None:
        super().__init__(sku=str(sku))


class MapToQuoteResponse(ts.Mapper, ports.QuoteResponse):

    def __init__(self, price_response: ports.PriceResponse) -> None:
        super().__init__(cents=price_response.cents)


class OrderActions(ts.Actions):

    def __init__(self, catalog_repository: ports.CatalogRepository) -> None:
        self._catalog_repository = catalog_repository

    def quote(self, quote_request: ports.QuoteRequest) -> ports.QuoteResponse:
        sku = domain.Sku(quote_request.sku)
        price_response = self._catalog_repository.price(MapToPriceRequest(sku))
        return MapToQuoteResponse(price_response)
