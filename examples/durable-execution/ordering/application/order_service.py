from __future__ import annotations

import tesser.application as ts

import ordering.application.relays as relays
import ordering.client as client
import ordering.domain as domain


class MapToOrderSpecFromSubmitOrderRequest(ts.Mapper, domain.OrderSpec):

    def __init__(self, submit_order_request: client.SubmitOrderRequest) -> None:
        super().__init__(
            order_id=submit_order_request.order_id,
            sku=submit_order_request.sku,
            quantity=submit_order_request.quantity,
        )


class MapToOrderSpecFromPlaceOrderRequest(ts.Mapper, domain.OrderSpec):

    def __init__(self, place_order_request: client.PlaceOrderRequest) -> None:
        super().__init__(
            order_id=place_order_request.order_id,
            sku=place_order_request.sku,
            quantity=place_order_request.quantity,
        )


class MapToOrderSpecFromPurchaseRequest(ts.Mapper, domain.OrderSpec):

    def __init__(self, purchase_request: client.PurchaseRequest) -> None:
        super().__init__(
            order_id=purchase_request.order_id,
            sku=purchase_request.sku,
            quantity=purchase_request.quantity,
        )


class MapToSubmitOrderResponse(ts.Mapper, client.SubmitOrderResponse):

    def __init__(
        self, start_order_orchestrator_response: relays.StartOrderOrchestratorResponse
    ) -> None:
        super().__init__(order_id=start_order_orchestrator_response.order_id)


class MapToPlaceOrderResponse(ts.Mapper, client.PlaceOrderResponse):

    def __init__(self, order_orchestrator_response: relays.OrderOrchestratorResponse) -> None:
        super().__init__(
            order_id=order_orchestrator_response.order_id,
            total_cents=order_orchestrator_response.total_cents,
        )


class MapToPurchaseResponse(ts.Mapper, client.PurchaseResponse):

    def __init__(
        self, purchase_orchestrator_response: relays.PurchaseOrchestratorResponse
    ) -> None:
        super().__init__(
            order_id=purchase_orchestrator_response.order_id,
            total_cents=purchase_orchestrator_response.total_cents,
            payment_reference=purchase_orchestrator_response.payment_reference,
        )


class OrderService(ts.ApplicationService):

    def __init__(  # tesser:debt TB081
        self,
        order_orchestrator_runner: relays.OrderOrchestratorRunner,
        purchase_orchestrator_runner: relays.PurchaseOrchestratorRunner,
    ) -> None:
        self._order_orchestrator_runner = order_orchestrator_runner
        self._purchase_orchestrator_runner = purchase_orchestrator_runner

    async def submit_order(
        self, submit_order_request: client.SubmitOrderRequest
    ) -> client.SubmitOrderResponse:
        order = domain.Order(MapToOrderSpecFromSubmitOrderRequest(submit_order_request))
        start_order_orchestrator_response = (
            await self._order_orchestrator_runner.start_order_orchestrator(
                relays.OrderOrchestratorRequest(order=order)
            )
        )
        return MapToSubmitOrderResponse(start_order_orchestrator_response)

    async def place_order(
        self, place_order_request: client.PlaceOrderRequest
    ) -> client.PlaceOrderResponse:
        order = domain.Order(MapToOrderSpecFromPlaceOrderRequest(place_order_request))
        order_orchestrator_response = await self._order_orchestrator_runner.run_order_orchestrator(
            relays.OrderOrchestratorRequest(order=order)
        )
        return MapToPlaceOrderResponse(order_orchestrator_response)

    async def purchase(self, purchase_request: client.PurchaseRequest) -> client.PurchaseResponse:
        order = domain.Order(MapToOrderSpecFromPurchaseRequest(purchase_request))
        purchase_orchestrator_response = (
            await self._purchase_orchestrator_runner.run_purchase_orchestrator(
                relays.PurchaseOrchestratorRequest(order=order)
            )
        )
        return MapToPurchaseResponse(purchase_orchestrator_response)
