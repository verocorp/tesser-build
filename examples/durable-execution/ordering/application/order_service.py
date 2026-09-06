from __future__ import annotations

import tesser.application as ts

import ordering.application.ports as ports
import ordering.client as client
import ordering.domain as domain


class MapToOrderSpec(ts.Mapper, domain.OrderSpec):

    def __init__(self, place_request: client.PlaceRequest) -> None:
        super().__init__(
            order_id=place_request.order_id, sku=place_request.sku, quantity=place_request.quantity
        )


class MapToStartRequest(ts.Mapper, ports.StartRequest):

    def __init__(self, order: domain.Order) -> None:
        super().__init__(
            order_id=str(order.identity), sku=str(order.sku), quantity=int(order.quantity)
        )


class MapToPlaceResponse(ts.Mapper, client.PlaceResponse):

    def __init__(self, start_response: ports.StartResponse) -> None:
        super().__init__(order_id=start_response.order_id)


class OrderService(ts.ApplicationService):

    def __init__(self, order_workflow: ports.OrderWorkflow) -> None:
        self._order_workflow = order_workflow

    async def place(self, place_request: client.PlaceRequest) -> client.PlaceResponse:
        order = domain.Order(MapToOrderSpec(place_request))
        start_response = await self._order_workflow.start(MapToStartRequest(order))
        return MapToPlaceResponse(start_response)
