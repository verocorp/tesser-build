from __future__ import annotations

import tesser.application as ts

import ordering.application.relays as relays
import ordering.client as client
import ordering.domain as domain


class MapToOrderSpec(ts.Mapper, domain.OrderSpec):

    def __init__(self, place_order_request: client.PlaceOrderRequest) -> None:
        super().__init__(
            order_id=place_order_request.order_id,
            sku=place_order_request.sku,
            quantity=place_order_request.quantity,
            note=place_order_request.note,
        )


class MapToPlaceOrderResponse(ts.Mapper, client.PlaceOrderResponse):

    def __init__(
        self, start_order_orchestrator_response: relays.StartOrderOrchestratorResponse
    ) -> None:
        super().__init__(order_id=start_order_orchestrator_response.order_id)


class OrderService(ts.ApplicationService):

    def __init__(self, order_orchestrator_runner: relays.OrderOrchestratorRunner) -> None:  # tesser:debt TB081
        self._order_orchestrator_runner = order_orchestrator_runner

    async def place_order(
        self, place_order_request: client.PlaceOrderRequest
    ) -> client.PlaceOrderResponse:
        order = domain.Order(MapToOrderSpec(place_order_request))
        start_order_orchestrator_response = (
            await self._order_orchestrator_runner.start_order_orchestrator(
                relays.OrderOrchestratorRequest(order=order)
            )
        )
        return MapToPlaceOrderResponse(start_order_orchestrator_response)
