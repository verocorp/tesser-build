from __future__ import annotations

import tesser.application as ts

import ordering.application.ports.order_workflow as order_workflow
import ordering.application.ports.quoting as quoting
import ordering.domain.order as order


class RunResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class MapToOrderSpec(ts.Mapper, order.OrderSpec):

    def __init__(self, request: order_workflow.StartRequest) -> None:
        super().__init__(order_id=request.order_id, sku=request.sku, quantity=request.quantity)


class MapToQuoteRequest(ts.Mapper, quoting.QuoteRequest):

    def __init__(self, running: order.Order) -> None:
        super().__init__(sku=str(running.sku))


class MapToPriceSpec(ts.Mapper, order.PriceSpec):

    def __init__(self, quoted: quoting.QuoteResponse) -> None:
        super().__init__(cents=quoted.cents)


class MapToRunResponse(ts.Mapper, RunResponse):

    def __init__(self, running: order.Order, total: order.Price) -> None:
        super().__init__(order_id=str(running.identity), total_cents=int(total))


class OrderOrchestrator(ts.Orchestrator):

    def __init__(self, job: ts.JobContext, quotes: quoting.Quoting) -> None:
        self._job = job
        self._quotes = quotes

    async def run(self, request: order_workflow.StartRequest) -> RunResponse:
        running = order.Order(MapToOrderSpec(request))
        quoted = await self._quotes.quote(self._job, MapToQuoteRequest(running))
        total = running.total(MapToPriceSpec(quoted))
        return MapToRunResponse(running, total)
