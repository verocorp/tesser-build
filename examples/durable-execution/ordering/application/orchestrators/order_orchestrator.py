from __future__ import annotations

import tesser.application as ts

import ordering.application.ports as ports
import ordering.domain as domain


class RunResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class MapToOrderSpec(ts.Mapper, domain.OrderSpec):

    def __init__(self, start_request: ports.StartRequest) -> None:
        super().__init__(
            order_id=start_request.order_id, sku=start_request.sku, quantity=start_request.quantity
        )


class MapToQuoteRequest(ts.Mapper, ports.QuoteRequest):

    def __init__(self, order: domain.Order) -> None:
        super().__init__(sku=str(order.sku))


class MapToPriceSpec(ts.Mapper, domain.PriceSpec):

    def __init__(self, quote_response: ports.QuoteResponse) -> None:
        super().__init__(cents=quote_response.cents)


class MapToRunResponse(ts.Mapper, RunResponse):

    def __init__(self, order: domain.Order, price: domain.Price) -> None:
        super().__init__(order_id=str(order.identity), total_cents=int(price))


class OrderOrchestrator(ts.Orchestrator):

    def __init__(self, job_context: ts.JobContext, quoting: ports.Quoting) -> None:
        self._job_context = job_context
        self._quoting = quoting

    async def run(self, start_request: ports.StartRequest) -> RunResponse:
        order = domain.Order(MapToOrderSpec(start_request))
        quote_response = await self._quoting.quote(self._job_context, MapToQuoteRequest(order))
        price = order.total(MapToPriceSpec(quote_response))
        return MapToRunResponse(order, price)
