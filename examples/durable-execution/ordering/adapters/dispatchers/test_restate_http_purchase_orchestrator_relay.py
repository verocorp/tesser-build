from __future__ import annotations

import asyncio
import os
import socket
import typing
import uuid

import tesser.testing as ts
import httpx
import hypercorn.asyncio as hypercorn_asyncio
import hypercorn.config as hypercorn_config
import hypercorn.typing as hypercorn_typing
import pytest
import restate

import ordering.adapters.activities as activities
import ordering.adapters.dispatchers as dispatchers
import ordering.adapters.workflows as workflows
import ordering.application.client as client
import ordering.application.relays as relays
import ordering.domain as domain


@ts.fake
class FakeOrderingApplicationClient(client.OrderingApplicationClient):

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICED,
            prices=(relays.Price(cents=250),),
            reasons=(),
        )


@ts.fake
class FakePurchaseApplicationClient(client.PurchaseApplicationClient):

    def __init__(self) -> None:
        self.taken: list[relays.TakePaymentRequest] = []

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        self.taken.append(take_payment_request)
        return relays.TakePaymentResponse(
            outcome=relays.TakePaymentOutcome.TAKEN,
            order_id=take_payment_request.order_id,
            payments=(
                relays.Payment(
                    reference=f"pay-{take_payment_request.order_id}",
                    cents=take_payment_request.cents,
                ),
            ),
            reasons=(),
        )


@ts.helper
def order_spec(order_id: str = "o1", sku: str = "widget", quantity: int = 2) -> domain.OrderSpec:
    return domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity)


@ts.helper
def pay_for_order_request(
    order: domain.Order,
    payment_method: domain.PaymentMethod = domain.PaymentMethod("card-4242"),
) -> relays.PayForOrderRequest:
    return relays.PayForOrderRequest(order=order, payment_method=payment_method)


class TestRestateHttpPurchaseOrchestratorRelay:

    async def test_running_calls_the_workflow_and_answers_with_its_result(self) -> None:
        suffix = uuid.uuid4().hex
        order_actions_service = restate.Service(f"OrderActions{suffix}")
        purchase_actions_service = restate.Service(f"PurchaseActions{suffix}")
        order_orchestrator_workflow = restate.Workflow(f"OrderOrchestrator{suffix}")
        purchase_orchestrator_workflow = restate.Workflow(f"PurchaseOrchestrator{suffix}")
        restate_price_product = activities.RestatePriceProduct(
            order_actions_service, FakeOrderingApplicationClient()
        )
        restate_take_payment = activities.RestateTakePayment(
            purchase_actions_service, FakePurchaseApplicationClient()
        )
        restate_confirm_order = workflows.RestateConfirmOrder(
            order_orchestrator_workflow, restate_price_product
        )
        restate_pay_for_order = workflows.RestatePayForOrder(
            purchase_orchestrator_workflow, restate_take_payment, restate_confirm_order
        )
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(
                    hypercorn_typing.ASGIFramework,
                    restate.app(
                        [
                            order_actions_service,
                            purchase_actions_service,
                            order_orchestrator_workflow,
                            purchase_orchestrator_workflow,
                        ]
                    ),
                ),
                hypercorn_config_config,
                shutdown_trigger=shutdown.wait,
            )
        )
        admin = httpx.AsyncClient(base_url=os.environ["RESTATE_ADMIN"], timeout=10.0)
        registered = httpx.Response(503)
        try:
            for _ in range(50):
                registered = await admin.post(
                    "/deployments",
                    json={"uri": f"http://{os.environ['DURABLE_CALLBACK_HOST']}:{port}", "force": True},
                )
                if registered.is_success:
                    break
                await asyncio.sleep(0.1)
            assert registered.is_success, registered.text

            order_id = str(uuid.uuid4())
            pay_for_order_response = await dispatchers.RestateHttpPurchaseOrchestratorRelay(
                os.environ["RESTATE_INGRESS"], restate_pay_for_order
            ).run_pay_for_order(pay_for_order_request(order=domain.Order(order_spec(order_id=order_id, quantity=2))))
            invoked = await admin.post(
                "/query",
                headers={"accept": "application/json"},
                json={
                    "query": "SELECT invoked_by, status, completion_result FROM sys_invocation "
                    f"WHERE target = 'PurchaseOrchestrator{suffix}/{order_id}/pay_for_order'"
                },
            )

            assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAID
            assert pay_for_order_response.order_id == order_id
            assert pay_for_order_response.purchases == (
                relays.Purchase(total_cents=500, payment_reference="pay-" + order_id),
            )
            assert [
                (row["invoked_by"], row["status"], row["completion_result"])
                for row in invoked.json()["rows"]
            ] == [("ingress", "completed", "success")]
        finally:
            if registered.is_success:
                await admin.delete(
                    f"/deployments/{registered.json()['id']}", params={"force": "true"}
                )
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)

    async def test_the_already_invoked_conflict_is_the_outcome_the_engine_crossing_adds(self) -> None:
        suffix = uuid.uuid4().hex
        order_actions_service = restate.Service(f"OrderActions{suffix}")
        purchase_actions_service = restate.Service(f"PurchaseActions{suffix}")
        order_orchestrator_workflow = restate.Workflow(f"OrderOrchestrator{suffix}")
        purchase_orchestrator_workflow = restate.Workflow(f"PurchaseOrchestrator{suffix}")
        restate_price_product = activities.RestatePriceProduct(
            order_actions_service, FakeOrderingApplicationClient()
        )
        restate_take_payment = activities.RestateTakePayment(
            purchase_actions_service, FakePurchaseApplicationClient()
        )
        restate_confirm_order = workflows.RestateConfirmOrder(
            order_orchestrator_workflow, restate_price_product
        )
        restate_pay_for_order = workflows.RestatePayForOrder(
            purchase_orchestrator_workflow, restate_take_payment, restate_confirm_order
        )
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(
                    hypercorn_typing.ASGIFramework,
                    restate.app(
                        [
                            order_actions_service,
                            purchase_actions_service,
                            order_orchestrator_workflow,
                            purchase_orchestrator_workflow,
                        ]
                    ),
                ),
                hypercorn_config_config,
                shutdown_trigger=shutdown.wait,
            )
        )
        admin = httpx.AsyncClient(base_url=os.environ["RESTATE_ADMIN"], timeout=10.0)
        registered = httpx.Response(503)
        try:
            for _ in range(50):
                registered = await admin.post(
                    "/deployments",
                    json={"uri": f"http://{os.environ['DURABLE_CALLBACK_HOST']}:{port}", "force": True},
                )
                if registered.is_success:
                    break
                await asyncio.sleep(0.1)
            assert registered.is_success, registered.text

            order_id = str(uuid.uuid4())
            restate_http_purchase_orchestrator_relay = dispatchers.RestateHttpPurchaseOrchestratorRelay(
                os.environ["RESTATE_INGRESS"], restate_pay_for_order
            )
            first = await restate_http_purchase_orchestrator_relay.run_pay_for_order(
                pay_for_order_request(order=domain.Order(order_spec(order_id=order_id)))
            )
            second = await restate_http_purchase_orchestrator_relay.run_pay_for_order(
                pay_for_order_request(order=domain.Order(order_spec(order_id=order_id)))
            )

            assert first.outcome is relays.PayForOrderOutcome.PAID
            assert second == relays.PayForOrderResponse(
                outcome=relays.PayForOrderOutcome.ALREADY_STARTED,
                order_id=order_id,
                purchases=(),
                reasons=(),
            )
        finally:
            if registered.is_success:
                await admin.delete(
                    f"/deployments/{registered.json()['id']}", params={"force": "true"}
                )
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)

    async def test_an_unreachable_ingress_is_a_fault(self) -> None:
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            unreachable = f"http://127.0.0.1:{closed.getsockname()[1]}"
        restate_confirm_order = workflows.RestateConfirmOrder(
            restate.Workflow("OrderOrchestrator"),
            activities.RestatePriceProduct(restate.Service("OrderActions"), FakeOrderingApplicationClient()),
        )
        restate_pay_for_order = workflows.RestatePayForOrder(
            restate.Workflow("PurchaseOrchestrator"),
            activities.RestateTakePayment(restate.Service("PurchaseActions"), FakePurchaseApplicationClient()),
            restate_confirm_order,
        )
        with pytest.raises(httpx.TransportError):
            await dispatchers.RestateHttpPurchaseOrchestratorRelay(
                unreachable, restate_pay_for_order
            ).run_pay_for_order(pay_for_order_request(order=domain.Order(order_spec())))
