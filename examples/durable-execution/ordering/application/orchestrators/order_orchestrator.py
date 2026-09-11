from __future__ import annotations

import tesser.application as ts

import ordering.application.relays as relays
import ordering.application.ports as ports
import ordering.domain as domain
import tesser.errors as errors


class MapToPriceProductRequest(ts.Mapper, relays.PriceProductRequest):

    def __init__(self, order: domain.Order) -> None:
        super().__init__(sku=str(order.sku))


class MapToPriceSpec(ts.Mapper, domain.PriceSpec):

    def __init__(self, price_product_response: relays.PriceProductResponse) -> None:
        super().__init__(cents=price_product_response.cents)


class MapToOrderOrchestratorResponse(ts.Mapper, relays.OrderOrchestratorResponse):

    def __init__(self, order: domain.Order, price: domain.Price) -> None:
        super().__init__(order_id=str(order.identity), total_cents=int(price))


class OrderOrchestrator(ts.Orchestrator):

    def __init__(self, order_actions_runner: relays.OrderActionsRunner) -> None:
        self._order_actions_runner = order_actions_runner

    async def run(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.OrderOrchestratorResponse:
        order = order_orchestrator_request.order
        price_product_response = await self._order_actions_runner.run_price_product(
            MapToPriceProductRequest(order)
        )
        try:
            price = order.total(MapToPriceSpec(price_product_response))
        except errors.DomainError as domain_error:
            raise ports.EngineRejected(domain_error.message) from domain_error
        return MapToOrderOrchestratorResponse(order, price)
