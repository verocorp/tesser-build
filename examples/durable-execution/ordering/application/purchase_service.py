from __future__ import annotations

import tesser.application as ts

import ordering.application.relays as relays
import ordering.client as client
import ordering.domain as domain


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

    def __init__(  # tesser:debt TB081
        self, purchase_orchestrator_runner: relays.PurchaseOrchestratorRunner
    ) -> None:
        self._purchase_orchestrator_runner = purchase_orchestrator_runner

    async def purchase(self, purchase_request: client.PurchaseRequest) -> client.PurchaseResponse:
        order = domain.Order(MapToOrderSpec(purchase_request))
        purchase_orchestrator_response = (
            await self._purchase_orchestrator_runner.run_purchase_orchestrator(
                relays.PurchaseOrchestratorRequest(order=order)
            )
        )
        return MapToPurchaseResponse(purchase_orchestrator_response)
