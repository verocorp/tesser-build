from __future__ import annotations

import tesser.application as ts

import ordering.application.relays.order_relay as order_relay
import ordering.domain.order as order


class RunResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class MapToQuoteRequest(ts.Mapper, order_relay.QuoteRequest):

    def __init__(self, running: order.Order) -> None:
        super().__init__(sku=str(running.sku))


class MapToPriceSpec(ts.Mapper, order.PriceSpec):

    def __init__(self, quoted: order_relay.QuoteResponse) -> None:
        super().__init__(cents=quoted.cents)


class MapToRunResponse(ts.Mapper, RunResponse):

    def __init__(self, running: order.Order, total: order.Price) -> None:
        super().__init__(order_id=str(running.identity), total_cents=int(total))


class OrderOrchestrator(ts.Orchestrator):

    def __init__(self, relay: order_relay.OrderRelay) -> None:
        self._relay = relay

    async def run(self, request: order_relay.StartRequest) -> RunResponse:
        running = request.order
        quoted = await self._relay.quote(MapToQuoteRequest(running))
        total = running.total(MapToPriceSpec(quoted))
        return MapToRunResponse(running, total)
