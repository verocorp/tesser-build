from __future__ import annotations

import tesser.application as ts

import ordering.application.ports.catalog_repository as catalog_repository
import ordering.application.relays.order_job_context as order_job_context
import ordering.domain.order as order


class MapToPriceRequest(ts.Mapper, catalog_repository.PriceRequest):

    def __init__(self, quoted_sku: order.Sku) -> None:
        super().__init__(sku=str(quoted_sku))


class MapToQuoteResponse(ts.Mapper, order_job_context.QuoteResponse):

    def __init__(self, priced: catalog_repository.PriceResponse) -> None:
        super().__init__(cents=priced.cents)


class OrderActions(ts.Actions):

    def __init__(self, catalog: catalog_repository.CatalogRepository) -> None:
        self._catalog = catalog

    def quote(self, request: order_job_context.QuoteRequest) -> order_job_context.QuoteResponse:
        quoted_sku = order.Sku(request.sku)
        priced = self._catalog.price(MapToPriceRequest(quoted_sku))
        return MapToQuoteResponse(priced)
