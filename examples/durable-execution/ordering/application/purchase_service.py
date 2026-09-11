from __future__ import annotations

import tesser.application as ts

import ordering.application.ports as ports
import ordering.application.relays as relays
import ordering.client as client
import ordering.domain as domain
import tesser.errors as errors


class MapToOrderSpec(ts.Mapper, domain.OrderSpec):

    def __init__(self, purchase_request: client.PurchaseRequest) -> None:
        super().__init__(
            order_id=purchase_request.order_id,
            sku=purchase_request.sku,
            quantity=purchase_request.quantity,
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


class PurchaseService(ts.ApplicationService):

    def __init__(
        self, purchase_orchestrator_runner: relays.PurchaseOrchestratorRunner
    ) -> None:
        self._purchase_orchestrator_runner = purchase_orchestrator_runner

    async def purchase(self, purchase_request: client.PurchaseRequest) -> client.PurchaseResponse:
        try:
            order = domain.Order(MapToOrderSpec(purchase_request))
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        try:
            purchase_orchestrator_response = (
                await self._purchase_orchestrator_runner.run_purchase_orchestrator(
                    relays.PurchaseOrchestratorRequest(order=order)
                )
            )
        except ports.EngineRejected as engine_error:
            raise client.Rejected(
                code="purchase_rejected", message=engine_error.message
            ) from engine_error
        except ports.EngineMissing as engine_error:
            raise client.Missing(
                code="purchase_rejected", message=engine_error.message
            ) from engine_error
        except ports.EngineConflict as engine_error:
            raise client.Conflict(
                code="purchase_rejected", message=engine_error.message
            ) from engine_error
        except ports.EngineUnavailable as engine_error:
            raise client.Unavailable(
                message="the ordering engine is unavailable"
            ) from engine_error
        return MapToPurchaseResponse(purchase_orchestrator_response)
