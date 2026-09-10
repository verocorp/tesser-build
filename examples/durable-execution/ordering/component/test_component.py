from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application as application
import ordering.application.relays as relays
import ordering.client as client
import ordering.component as component


@ts.fake
class FakeOrderOrchestratorRunner(relays.OrderOrchestratorRunner):  # tesser:debt TB072

    def __init__(self) -> None:
        self.started: list[str] = []
        self.ran: list[str] = []

    async def start_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.StartOrderOrchestratorResponse:
        self.started.append(str(order_orchestrator_request.order.identity))
        return relays.StartOrderOrchestratorResponse(
            order_id=str(order_orchestrator_request.order.identity)
        )

    async def run_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.OrderOrchestratorResponse:
        self.ran.append(str(order_orchestrator_request.order.identity))
        return relays.OrderOrchestratorResponse(
            order_id=str(order_orchestrator_request.order.identity), total_cents=500
        )


@ts.fake
class FakePurchaseOrchestratorRunner(relays.PurchaseOrchestratorRunner):  # tesser:debt TB072

    def __init__(self) -> None:
        self.ran: list[str] = []

    async def run_purchase_orchestrator(
        self, purchase_orchestrator_request: relays.PurchaseOrchestratorRequest
    ) -> relays.PurchaseOrchestratorResponse:
        self.ran.append(str(purchase_orchestrator_request.order.identity))
        return relays.PurchaseOrchestratorResponse(
            order_id=str(purchase_orchestrator_request.order.identity),
            total_cents=500,
            payment_reference="pay-o1",
        )


class TestClient:

    def test_each_use_case_reaches_the_service_that_owns_it(self) -> None:
        fake_order_orchestrator_runner = FakeOrderOrchestratorRunner()  # tesser:debt TB085
        fake_purchase_orchestrator_runner = FakePurchaseOrchestratorRunner()  # tesser:debt TB085
        ordering_client: client.OrderingClient = component.Ordering.Client(
            application.OrderService(fake_order_orchestrator_runner),
            application.PurchaseService(fake_purchase_orchestrator_runner),
        )
        submit_order_response = asyncio.run(
            ordering_client.submit_order(
                client.SubmitOrderRequest(order_id="s1", sku="widget", quantity=2)
            )
        )
        place_order_response = asyncio.run(
            ordering_client.place_order(
                client.PlaceOrderRequest(order_id="p1", sku="widget", quantity=2)
            )
        )
        purchase_response = asyncio.run(
            ordering_client.purchase(client.PurchaseRequest(order_id="u1", sku="widget", quantity=2))
        )
        assert submit_order_response.order_id == "s1"
        assert place_order_response.total_cents == 500
        assert purchase_response.payment_reference == "pay-o1"
        assert fake_order_orchestrator_runner.started == ["s1"]
        assert fake_order_orchestrator_runner.ran == ["p1"]
        assert fake_purchase_orchestrator_runner.ran == ["u1"]


class TestOrdering:

    def test_the_component_publishes_the_restate_runtime_it_wired(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://localhost:8080")))
        try:
            declared = {
                ordering.restate_order_runtime.order_actions_service.name: sorted(
                    ordering.restate_order_runtime.order_actions_service.handlers
                ),
                ordering.restate_order_runtime.order_orchestrator_workflow.name: sorted(
                    ordering.restate_order_runtime.order_orchestrator_workflow.handlers
                ),
                ordering.restate_order_runtime.purchase_actions_service.name: sorted(
                    ordering.restate_order_runtime.purchase_actions_service.handlers
                ),
                ordering.restate_order_runtime.purchase_orchestrator_workflow.name: sorted(
                    ordering.restate_order_runtime.purchase_orchestrator_workflow.handlers
                ),
            }
        finally:
            ordering.close()
        assert declared == {
            "OrderActions": ["price_product"],
            "OrderOrchestrator": ["run"],
            "PurchaseActions": ["take_payment"],
            "PurchaseOrchestrator": ["run"],
        }


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = component.Spec(ingress="http://localhost:8080")
        config = component.Config(spec)
        assert config.ingress == spec.ingress
