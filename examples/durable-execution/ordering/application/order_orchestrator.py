from __future__ import annotations

import tesser.application as ts

import ordering.application.ports.quotes as quotes
import ordering.client.client as client
import ordering.domain.order as order


class MapToOrderSpec(ts.Mapper, order.OrderSpec):

    def __init__(self, request: client.RunRequest) -> None:
        super().__init__(order_id=request.order_id, sku=request.sku, quantity=request.quantity)


class MapToQuoteRequest(ts.Mapper, quotes.QuoteRequest):

    def __init__(self, running: order.Order) -> None:
        super().__init__(sku=str(running.sku))


class MapToPriceSpec(ts.Mapper, order.PriceSpec):

    def __init__(self, quoted: quotes.QuoteResponse) -> None:
        super().__init__(cents=quoted.cents)


class MapToRunResponse(ts.Mapper, client.RunResponse):

    def __init__(self, running: order.Order, total: order.Price) -> None:
        super().__init__(order_id=str(running.identity), total_cents=int(total))


class OrderOrchestrator(ts.ApplicationService):

    def __init__(self, quotes: quotes.Quotes) -> None:
        self._quotes = quotes

    async def run(self, request: client.RunRequest) -> client.RunResponse:
        running = order.Order(MapToOrderSpec(request))
        quoted = await self._quotes.quote(MapToQuoteRequest(running))
        total = running.total(MapToPriceSpec(quoted))
        return MapToRunResponse(running, total)
