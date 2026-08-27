from __future__ import annotations

import tesser.application as ts

import ordering.application.ports.catalog_repository as catalog_repository
import ordering.client.client as client
import ordering.domain.order as order


class MapToOrderSpec(ts.Mapper, order.OrderSpec):

    def __init__(self, request: client.RunRequest) -> None:
        super().__init__(order_id=request.order_id, sku=request.sku, quantity=request.quantity)


class MapToPriceRequest(ts.Mapper, catalog_repository.PriceRequest):

    def __init__(self, running: order.Order) -> None:
        super().__init__(sku=str(running.sku))


class MapToPriceSpec(ts.Mapper, order.PriceSpec):

    def __init__(self, priced: catalog_repository.PriceResponse) -> None:
        super().__init__(cents=priced.cents)


class MapToRunResponse(ts.Mapper, client.RunResponse):

    def __init__(self, running: order.Order, total: order.Price) -> None:
        super().__init__(order_id=str(running.identity), total_cents=int(total))


class OrderOrchestrator(ts.ApplicationService):

    def __init__(self, catalog: catalog_repository.CatalogRepository) -> None:
        self._catalog = catalog

    async def run(self, request: client.RunRequest) -> client.RunResponse:
        running = order.Order(MapToOrderSpec(request))
        priced = await self._catalog.price(MapToPriceRequest(running))
        total = running.total(MapToPriceSpec(priced))
        return MapToRunResponse(running, total)
