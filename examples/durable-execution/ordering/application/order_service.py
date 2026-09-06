from __future__ import annotations

import tesser.application as ts

import ordering.application.relays.order_relay as order_relay
import ordering.client.client as client
import ordering.domain.order as order


class MapToOrderSpec(ts.Mapper, order.OrderSpec):

    def __init__(self, request: client.PlaceRequest) -> None:
        super().__init__(order_id=request.order_id, sku=request.sku, quantity=request.quantity)


class MapToPlaceResponse(ts.Mapper, client.PlaceResponse):

    def __init__(self, started: order_relay.StartResponse) -> None:
        super().__init__(order_id=started.order_id)


class OrderService(ts.ApplicationService):

    def __init__(self, relay: order_relay.OrderRelay) -> None:
        self._relay = relay

    async def place(self, request: client.PlaceRequest) -> client.PlaceResponse:
        placed = order.Order(MapToOrderSpec(request))
        started = await self._relay.start(order_relay.StartRequest(order=placed))
        return MapToPlaceResponse(started)
