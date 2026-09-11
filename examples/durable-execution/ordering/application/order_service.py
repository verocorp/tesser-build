from __future__ import annotations

import tesser.application as ts

import ordering.application.ports as ports
import ordering.application.relays as relays
import ordering.client as client
import ordering.domain as domain
import tesser.errors as errors


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


class OrderService(ts.ApplicationService):

    def __init__(self, order_orchestrator_runner: relays.OrderOrchestratorRunner) -> None:
        self._order_orchestrator_runner = order_orchestrator_runner

    async def submit_order(
        self, submit_order_request: client.SubmitOrderRequest
    ) -> client.SubmitOrderResponse:
        try:
            order = domain.Order(MapToOrderSpecFromSubmitOrderRequest(submit_order_request))
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        try:
            start_order_orchestrator_response = (
                await self._order_orchestrator_runner.start_order_orchestrator(
                    relays.OrderOrchestratorRequest(order=order)
                )
            )
        except ports.EngineRejected as engine_error:
            raise client.Rejected(
                code="order_rejected", message=engine_error.message
            ) from engine_error
        except ports.EngineMissing as engine_error:
            raise client.Missing(
                code="order_rejected", message=engine_error.message
            ) from engine_error
        except ports.EngineConflict as engine_error:
            raise client.Conflict(
                code="order_rejected", message=engine_error.message
            ) from engine_error
        except ports.EngineUnavailable as engine_error:
            raise client.Unavailable(
                message="the ordering engine is unavailable"
            ) from engine_error
        return MapToSubmitOrderResponse(start_order_orchestrator_response)

    async def place_order(
        self, place_order_request: client.PlaceOrderRequest
    ) -> client.PlaceOrderResponse:
        try:
            order = domain.Order(MapToOrderSpecFromPlaceOrderRequest(place_order_request))
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        try:
            order_orchestrator_response = (
                await self._order_orchestrator_runner.run_order_orchestrator(
                    relays.OrderOrchestratorRequest(order=order)
                )
            )
        except ports.EngineRejected as engine_error:
            raise client.Rejected(
                code="order_rejected", message=engine_error.message
            ) from engine_error
        except ports.EngineMissing as engine_error:
            raise client.Missing(
                code="order_rejected", message=engine_error.message
            ) from engine_error
        except ports.EngineConflict as engine_error:
            raise client.Conflict(
                code="order_rejected", message=engine_error.message
            ) from engine_error
        except ports.EngineUnavailable as engine_error:
            raise client.Unavailable(
                message="the ordering engine is unavailable"
            ) from engine_error
        return MapToPlaceOrderResponse(order_orchestrator_response)
