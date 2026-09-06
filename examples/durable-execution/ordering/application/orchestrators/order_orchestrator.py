from __future__ import annotations

import tesser.application as ts

import ordering.application.relays.order_job_context as order_job_context
import ordering.application.relays.order_relay as order_relay
import ordering.domain.order as order


class MapToQuoteRequest(ts.Mapper, order_job_context.QuoteRequest):

    def __init__(self, running: order.Order) -> None:
        super().__init__(sku=str(running.sku))


class MapToPriceSpec(ts.Mapper, order.PriceSpec):

    def __init__(self, quoted: order_job_context.QuoteResponse) -> None:
        super().__init__(cents=quoted.cents)


class MapToRunResponse(ts.Mapper, order_relay.RunResponse):

    def __init__(self, running: order.Order, total: order.Price) -> None:
        super().__init__(order_id=str(running.identity), total_cents=int(total))


class OrderOrchestrator(ts.Orchestrator):

    def __init__(self, job: order_job_context.OrderJobContext) -> None:
        self._job = job

    async def run(self, request: order_relay.StartRequest) -> order_relay.RunResponse:
        running = request.order
        quoted = await self._job.quote(MapToQuoteRequest(running))
        total = running.total(MapToPriceSpec(quoted))
        return MapToRunResponse(running, total)
