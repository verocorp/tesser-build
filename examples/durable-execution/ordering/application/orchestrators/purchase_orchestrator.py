from __future__ import annotations

import tesser.application as ts

import ordering.application.relays as relays
import ordering.application.ports as ports
import ordering.domain as domain
import tesser.errors as errors


class MapToPurchaseSpec(ts.Mapper, domain.PurchaseSpec):

    def __init__(
        self, order: domain.Order, order_orchestrator_response: relays.OrderOrchestratorResponse
    ) -> None:
        super().__init__(
            order_id=str(order.identity),
            priced_order_id=order_orchestrator_response.order_id,
            total_cents=order_orchestrator_response.total_cents,
        )


class MapToTakePaymentRequest(ts.Mapper, relays.TakePaymentRequest):

    def __init__(self, purchase: domain.Purchase) -> None:
        super().__init__(order_id=str(purchase.identity), cents=int(purchase.total))


class MapToPaymentSpec(ts.Mapper, domain.PaymentSpec):

    def __init__(self, take_payment_response: relays.TakePaymentResponse) -> None:
        super().__init__(
            order_id=take_payment_response.order_id,
            reference=take_payment_response.reference,
            cents=take_payment_response.cents,
        )


class MapToPurchaseOrchestratorResponse(ts.Mapper, relays.PurchaseOrchestratorResponse):

    def __init__(self, purchase: domain.Purchase, payment: domain.Payment) -> None:
        super().__init__(
            order_id=str(purchase.identity),
            total_cents=int(purchase.total),
            payment_reference=str(payment.reference),
        )


class PurchaseOrchestrator(ts.Orchestrator):

    def __init__(
        self,
        purchase_actions_runner: relays.PurchaseActionsRunner,
        order_orchestrator_runner: relays.OrderOrchestratorRunner,
    ) -> None:
        self._purchase_actions_runner = purchase_actions_runner
        self._order_orchestrator_runner = order_orchestrator_runner

    async def run(
        self, purchase_orchestrator_request: relays.PurchaseOrchestratorRequest
    ) -> relays.PurchaseOrchestratorResponse:
        order = purchase_orchestrator_request.order
        order_orchestrator_response = await self._order_orchestrator_runner.run_order_orchestrator(
            relays.OrderOrchestratorRequest(order=order)
        )
        try:
            purchase = domain.Purchase(MapToPurchaseSpec(order, order_orchestrator_response))
        except errors.DomainError as domain_error:
            raise ports.EngineRejected(domain_error.message) from domain_error
        take_payment_response = await self._purchase_actions_runner.run_take_payment(
            MapToTakePaymentRequest(purchase)
        )
        try:
            payment = purchase.paid(MapToPaymentSpec(take_payment_response))
        except errors.DomainError as domain_error:
            raise ports.EngineRejected(domain_error.message) from domain_error
        return MapToPurchaseOrchestratorResponse(purchase, payment)
