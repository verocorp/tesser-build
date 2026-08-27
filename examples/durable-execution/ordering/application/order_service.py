from __future__ import annotations

import tesser.application as ts

import ordering.application.ports.order_workflow as order_workflow
import ordering.client.client as client
import ordering.domain.order as order


class MapToOrderSpec(ts.Mapper, order.OrderSpec):

    def __init__(self, request: client.PlaceRequest) -> None:
        super().__init__(order_id=request.order_id, sku=request.sku, quantity=request.quantity)


class MapToStartRequest(ts.Mapper, order_workflow.StartRequest):

    def __init__(self, placed: order.Order) -> None:
        super().__init__(
            order_id=str(placed.identity), sku=str(placed.sku), quantity=int(placed.quantity)
        )


class MapToPlaceResponse(ts.Mapper, client.PlaceResponse):

    def __init__(self, started: order_workflow.StartResponse) -> None:
        super().__init__(order_id=started.order_id)


class OrderService(ts.ApplicationService):

    def __init__(self, workflows: order_workflow.OrderWorkflow) -> None:
        self._workflows = workflows

    def place(self, request: client.PlaceRequest) -> client.PlaceResponse:
        placed = order.Order(MapToOrderSpec(request))
        started = self._workflows.start(MapToStartRequest(placed))
        return MapToPlaceResponse(started)
