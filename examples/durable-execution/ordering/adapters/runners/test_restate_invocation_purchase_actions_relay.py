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


class TestRestateInvocationPurchaseActionsRelay:

    def test_running_take_payment_journals_a_call_to_the_runtimes_handler(self) -> None:
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
                "query": "SELECT target, invoked_by_service_name, completion_result "
                "FROM sys_invocation "
                "WHERE invoked_by_target = 'PurchaseOrchestrator/" + order_id + "/pay_for_order' "
                "ORDER BY created_at"
            },
        )
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAID
        assert pay_for_order_response.purchases[0].payment_reference == "pay-" + order_id
        assert pay_for_order_response.purchases[0].total_cents == 500
        assert [
            (row["target"], row["invoked_by_service_name"], row["completion_result"])
            for row in response.json()["rows"]
        ] == [
            ("OrderOrchestrator/" + order_id + "/confirm_order", "PurchaseOrchestrator", "success"),
            ("PurchaseActions/take_payment", "PurchaseOrchestrator", "success"),
        ]

    def test_no_payment_is_taken_for_an_order_that_was_not_confirmed(self) -> None:
        order_id = str(uuid.uuid4())
        pay_for_order_response = asyncio.run(
            runners.RestateIngressPurchaseOrchestratorRelay(
                os.environ["RESTATE_INGRESS"],
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).run_pay_for_order(pay_for_order_request(order_id=order_id, sku="nothing"))
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target FROM sys_invocation "
                "WHERE invoked_by_target = 'PurchaseOrchestrator/" + order_id + "/pay_for_order'"
            },
        )
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED
        assert pay_for_order_response.reasons == ("no price for sku 'nothing'",)
        assert [row["target"] for row in response.json()["rows"]] == [
            "OrderOrchestrator/" + order_id + "/confirm_order"
        ]

    def test_a_declined_charge_ends_the_call_as_an_outcome_not_a_failure(self) -> None:
        order_id = str(uuid.uuid4())
        pay_for_order_response = asyncio.run(
            runners.RestateIngressPurchaseOrchestratorRelay(
                os.environ["RESTATE_INGRESS"],
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).run_pay_for_order(
                pay_for_order_request(order_id=order_id, payment_method="declined")
            )
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target, completion_result FROM sys_invocation "
                "WHERE invoked_by_target = 'PurchaseOrchestrator/" + order_id + "/pay_for_order' "
                "AND target_service_name = 'PurchaseActions'"
            },
        )
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAYMENT_DECLINED
        assert pay_for_order_response.reasons == (
            f"the processor declined the charge for order {order_id!r}",
        )
        assert [
            (row["target"], row["completion_result"]) for row in response.json()["rows"]
        ] == [("PurchaseActions/take_payment", "success")]
