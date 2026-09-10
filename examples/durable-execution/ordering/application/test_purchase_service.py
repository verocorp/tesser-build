from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application as application
import ordering.application.relays as relays
import ordering.client as client


@ts.fake
class FakePurchaseOrchestratorRunner(relays.PurchaseOrchestratorRunner):  # tesser:debt TB072

    def __init__(self) -> None:
        self.ran: list[relays.PurchaseOrchestratorRequest] = []

    async def run_purchase_orchestrator(
        self, purchase_orchestrator_request: relays.PurchaseOrchestratorRequest
    ) -> relays.PurchaseOrchestratorResponse:
        self.ran.append(purchase_orchestrator_request)
        return relays.PurchaseOrchestratorResponse(
            order_id=str(purchase_orchestrator_request.order.identity),
            total_cents=250 * int(purchase_orchestrator_request.order.quantity),
            payment_reference=f"pay-{purchase_orchestrator_request.order.identity}",
        )


@ts.helper
def purchase_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> client.PurchaseRequest:
    return client.PurchaseRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestPurchaseService:

    def test_purchasing_answers_the_order_id_the_total_and_the_payment_reference(self) -> None:
        purchase_response = asyncio.run(
            application.PurchaseService(FakePurchaseOrchestratorRunner()).purchase(
                purchase_request(quantity=3)
            )
        )
        assert purchase_response.order_id == "o1"
        assert purchase_response.total_cents == 750
        assert purchase_response.payment_reference == "pay-o1"

    def test_purchasing_runs_the_orchestrator_for_the_order_it_built_and_waits(self) -> None:
        fake_purchase_orchestrator_runner = FakePurchaseOrchestratorRunner()  # tesser:debt TB085
        asyncio.run(
            application.PurchaseService(fake_purchase_orchestrator_runner).purchase(
                purchase_request(order_id="o2", sku="gadget", quantity=3)
            )
        )
        assert [
            (str(r.order.identity), str(r.order.sku), int(r.order.quantity))
            for r in fake_purchase_orchestrator_runner.ran
        ] == [("o2", "gadget", 3)]
