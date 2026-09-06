from __future__ import annotations

import tesser.application as ts

import ordering.application.relays as relays
import ordering.domain as domain


class MapToPrepareQuoteRequest(ts.Mapper, relays.PrepareQuoteRequest):

    def __init__(self, order: domain.Order) -> None:
        super().__init__(sku=str(order.sku))


class MapToPriceSpec(ts.Mapper, domain.PriceSpec):

    def __init__(self, prepare_quote_response: relays.PrepareQuoteResponse) -> None:
        super().__init__(cents=prepare_quote_response.cents)


class MapToOrderOrchestratorResponse(ts.Mapper, relays.OrderOrchestratorResponse):

    def __init__(self, order: domain.Order, price: domain.Price) -> None:
        super().__init__(order_id=str(order.identity), total_cents=int(price))


class OrderOrchestrator(ts.Orchestrator):

    def __init__(self, order_actions_runner: relays.OrderActionsRunner) -> None:
        self._order_actions_runner = order_actions_runner

    async def run(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.OrderOrchestratorResponse:
        order = order_orchestrator_request.order  # tesser:debt TB082
        prepare_quote_response = await self._order_actions_runner.run_prepare_quote(
            MapToPrepareQuoteRequest(order)
        )
        price = order.total(MapToPriceSpec(prepare_quote_response))
        return MapToOrderOrchestratorResponse(order, price)
