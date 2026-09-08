from __future__ import annotations

import tesser.application as ts

import ordering.application.relays as relays
import ordering.client as client
import ordering.domain as domain


class MapToOrderSpec(ts.Mapper, domain.OrderSpec):

    def __init__(self, submit_order_request: client.SubmitOrderRequest) -> None:
        super().__init__(
            order_id=submit_order_request.order_id,
            sku=submit_order_request.sku,
            quantity=submit_order_request.quantity,
        )


class MapToSubmitOrderResponse(ts.Mapper, client.SubmitOrderResponse):

    def __init__(
        self, start_order_orchestrator_response: relays.StartOrderOrchestratorResponse
    ) -> None:
        super().__init__(order_id=start_order_orchestrator_response.order_id)


class OrderService(ts.ApplicationService):

    def __init__(self, order_orchestrator_runner: relays.OrderOrchestratorRunner) -> None:  # tesser:debt TB081
        self._order_orchestrator_runner = order_orchestrator_runner

    async def submit_order(
        self, submit_order_request: client.SubmitOrderRequest
    ) -> client.SubmitOrderResponse:
        order = domain.Order(MapToOrderSpec(submit_order_request))
        start_order_orchestrator_response = (
            await self._order_orchestrator_runner.start_order_orchestrator(
                relays.OrderOrchestratorRequest(order=order)
            )
        )
        return MapToSubmitOrderResponse(start_order_orchestrator_response)
