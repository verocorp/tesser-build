from __future__ import annotations

import tesser.application as ts

import ordering.application.ports.order_actions as order_actions
import ordering.application.ports.order_workflow as order_workflow
import ordering.domain.order as order


class RunResponse(ts.Response):

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents


class MapToOrderSpec(ts.Mapper, order.OrderSpec):

    def __init__(self, request: order_workflow.StartRequest) -> None:
        super().__init__(order_id=request.order_id, sku=request.sku, quantity=request.quantity)


class MapToQuoteRequest(ts.Mapper, order_actions.QuoteRequest):

    def __init__(self, running: order.Order) -> None:
        super().__init__(sku=str(running.sku))


class MapToPriceSpec(ts.Mapper, order.PriceSpec):

    def __init__(self, quoted: order_actions.QuoteResponse) -> None:
        super().__init__(cents=quoted.cents)


class MapToRunResponse(ts.Mapper, RunResponse):

    def __init__(self, running: order.Order, total: order.Price) -> None:
        super().__init__(order_id=str(running.identity), total_cents=int(total))


class OrderOrchestrator(ts.Orchestrator):

    def __init__(self, actions: order_actions.OrderActions) -> None:
        self._actions = actions

    async def run(self, request: order_workflow.StartRequest) -> RunResponse:
        running = order.Order(MapToOrderSpec(request))
        quoted = await self._actions.quote(MapToQuoteRequest(running))
        total = running.total(MapToPriceSpec(quoted))
        return MapToRunResponse(running, total)
