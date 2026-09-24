from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application as application
import ordering.application.relays as relays
import ordering.client as client
import ordering.component as component


@ts.fake
class FakeOrderOrchestratorRelay(relays.OrderOrchestratorRelay):

    def __init__(self) -> None:
        self.started: list[str] = []
        self.ran: list[str] = []

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        self.started.append(str(confirm_order_request.order.identity))
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED,
            order_id=str(confirm_order_request.order.identity),
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        self.ran.append(str(confirm_order_request.order.identity))
        return relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id=str(confirm_order_request.order.identity),
            confirmed_orders=(relays.ConfirmedOrder(total_cents=500),),
            reasons=(),
        )


@ts.fake
class FakePurchaseOrchestratorRelay(relays.PurchaseOrchestratorRelay):

    def __init__(self) -> None:
        self.ran: list[str] = []

    async def run_pay_for_order(
        self, pay_for_order_request: relays.PayForOrderRequest
    ) -> relays.PayForOrderResponse:
        self.ran.append(str(pay_for_order_request.order.identity))
        return relays.PayForOrderResponse(
            outcome=relays.PayForOrderOutcome.PAID,
            order_id=str(pay_for_order_request.order.identity),
            purchases=(relays.Purchase(total_cents=500, payment_reference="pay-o1"),),
            reasons=(),
        )


class TestClient:

    def test_each_use_case_reaches_the_service_that_owns_it(self) -> None:
        fake_order_orchestrator_relay = FakeOrderOrchestratorRelay()
        fake_purchase_orchestrator_relay = FakePurchaseOrchestratorRelay()
        ordering_client: client.OrderingClient = component.Ordering.Client(
            application.OrderService(fake_order_orchestrator_relay),
            application.PurchaseService(fake_purchase_orchestrator_relay),
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
        make_order_payment_response = asyncio.run(
            ordering_client.make_order_payment(
                client.MakeOrderPaymentRequest(
                    order_id="u1", sku="widget", quantity=2, payment_method="card-4242"
                )
            )
        )
        assert submit_order_response.order_id == "s1"
        assert place_order_response.total_cents == 500
        assert make_order_payment_response.payment_reference == "pay-o1"
        assert fake_order_orchestrator_relay.started == ["s1"]
        assert fake_order_orchestrator_relay.ran == ["p1"]
        assert fake_purchase_orchestrator_relay.ran == ["u1"]


class TestOrdering:

    def test_the_component_publishes_the_engine_containers_it_registered_into(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://localhost:8080")))
        try:
            declared = {
                ordering.order_actions_service.name: sorted(
                    ordering.order_actions_service.handlers
                ),
                ordering.order_orchestrator_workflow.name: sorted(
                    ordering.order_orchestrator_workflow.handlers
                ),
                ordering.purchase_actions_service.name: sorted(
                    ordering.purchase_actions_service.handlers
                ),
                ordering.purchase_orchestrator_workflow.name: sorted(
                    ordering.purchase_orchestrator_workflow.handlers
                ),
            }
        finally:
            ordering.close()
        assert declared == {
            "OrderActions": ["price_product"],
            "OrderOrchestrator": ["confirm_order"],
            "PurchaseActions": ["take_payment"],
            "PurchaseOrchestrator": ["pay_for_order"],
        }


    def test_every_container_bounds_its_retries_and_only_the_workflows_face_the_ingress(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://localhost:8080")))
        try:
            declared = {
                registered.name: (
                    registered.ingress_private,
                    registered.invocation_retry_policy.max_attempts
                    if registered.invocation_retry_policy
                    else None,
                    registered.invocation_retry_policy.on_max_attempts
                    if registered.invocation_retry_policy
                    else None,
                )
                for registered in (
                    ordering.order_actions_service,
                    ordering.purchase_actions_service,
                    ordering.order_orchestrator_workflow,
                    ordering.purchase_orchestrator_workflow,
                )
            }
        finally:
            ordering.close()
        assert declared == {
            "OrderActions": (True, 5, "pause"),
            "PurchaseActions": (True, 5, "pause"),
            "OrderOrchestrator": (None, 5, "pause"),
            "PurchaseOrchestrator": (None, 5, "pause"),
        }


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = component.Spec(ingress="http://localhost:8080")
        config = component.Config(spec)
        assert config.ingress == spec.ingress
