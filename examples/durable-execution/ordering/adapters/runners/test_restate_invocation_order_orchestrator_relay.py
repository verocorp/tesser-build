from __future__ import annotations

import asyncio
import os
import uuid

import tesser.testing as ts
import httpx

import ordering.adapters.runners as runners
import ordering.adapters.runtimes as runtimes
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

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
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
def confirm_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.ConfirmOrderRequest:
    return relays.ConfirmOrderRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


@ts.helper
def pay_for_order_request(
    order_id: str = "o1",
    sku: str = "widget",
    quantity: int = 2,
    payment_method: str = "card-4242",
) -> relays.PayForOrderRequest:
    return relays.PayForOrderRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity)),
        payment_method=domain.PaymentMethod(payment_method),
    )


class TestRestateInvocationOrderOrchestratorRelay:

    def test_running_journals_a_call_to_the_order_workflow_keyed_by_the_orders_id(self) -> None:
        order_id = str(uuid.uuid4())
        pay_for_order_response = asyncio.run(
            runners.RestateIngressPurchaseOrchestratorRelay(
                os.environ["RESTATE_INGRESS"],
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).run_pay_for_order(pay_for_order_request(order_id=order_id))
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target_service_key, invoked_by_service_name, invoked_by_target, "
                "completion_result FROM sys_invocation "
                "WHERE target = 'OrderOrchestrator/" + order_id + "/confirm_order'"
            },
        )
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAID
        assert [
            (
                row["target_service_key"],
                row["invoked_by_service_name"],
                row["invoked_by_target"],
                row["completion_result"],
            )
            for row in response.json()["rows"]
        ] == [
            (
                order_id,
                "PurchaseOrchestrator",
                "PurchaseOrchestrator/" + order_id + "/pay_for_order",
                "success",
            )
        ]

    def test_the_key_is_the_id_as_it_is_because_no_path_is_formed_inside_the_engine(self) -> None:
        order_id = "../admin?x=1#f-" + str(uuid.uuid4())
        pay_for_order_response = asyncio.run(
            runners.RestateIngressPurchaseOrchestratorRelay(
                os.environ["RESTATE_INGRESS"],
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).run_pay_for_order(pay_for_order_request(order_id=order_id))
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target, target_service_key FROM sys_invocation "
                "WHERE invoked_by_target = 'PurchaseOrchestrator/" + order_id + "/pay_for_order' "
                "AND target_service_name = 'OrderOrchestrator'"
            },
        )
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAID
        assert [
            (row["target"], row["target_service_key"]) for row in response.json()["rows"]
        ] == [("OrderOrchestrator/" + order_id + "/confirm_order", order_id)]

    def test_the_already_invoked_conflict_is_the_outcome_the_engine_crossing_adds(self) -> None:
        order_id = str(uuid.uuid4())
        restate_order_runtime = runtimes.RestateOrderRuntime(
            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
        )
        confirm_order_response = asyncio.run(
            runners.RestateIngressOrderOrchestratorRelay(
                os.environ["RESTATE_INGRESS"], restate_order_runtime
            ).run_confirm_order(confirm_order_request(order_id=order_id))
        )
        pay_for_order_response = asyncio.run(
            runners.RestateIngressPurchaseOrchestratorRelay(
                os.environ["RESTATE_INGRESS"], restate_order_runtime
            ).run_pay_for_order(pay_for_order_request(order_id=order_id))
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target, invoked_by, completion_result FROM sys_invocation "
                "WHERE target_service_key = '" + order_id + "' ORDER BY created_at"
            },
        )
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED
        assert pay_for_order_response.reasons == ("the order was already started",)
        assert [
            (row["target"], row["invoked_by"], row["completion_result"])
            for row in response.json()["rows"]
        ] == [
            ("OrderOrchestrator/" + order_id + "/confirm_order", "ingress", "success"),
            ("PurchaseOrchestrator/" + order_id + "/pay_for_order", "ingress", "success"),
        ]
