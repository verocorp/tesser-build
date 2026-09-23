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


class TestRestateInvocationOrderActionsRelay:

    def test_running_price_product_journals_a_call_to_the_runtimes_handler(self) -> None:
        order_id = str(uuid.uuid4())
        confirm_order_response = asyncio.run(
            runners.RestateIngressOrderOrchestratorRelay(
                os.environ["RESTATE_INGRESS"],
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).run_confirm_order(confirm_order_request(order_id=order_id))
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target, invoked_by_service_name, completion_result "
                "FROM sys_invocation "
                "WHERE invoked_by_target = 'OrderOrchestrator/" + order_id + "/confirm_order'"
            },
        )
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
        assert confirm_order_response.confirmed_orders[0].total_cents == 500
        assert [
            (row["target"], row["invoked_by_service_name"], row["completion_result"])
            for row in response.json()["rows"]
        ] == [("OrderActions/price_product", "OrderOrchestrator", "success")]

    def test_a_price_the_catalog_does_not_hold_ends_the_call_as_an_outcome_not_a_failure(
        self,
    ) -> None:
        order_id = str(uuid.uuid4())
        confirm_order_response = asyncio.run(
            runners.RestateIngressOrderOrchestratorRelay(
                os.environ["RESTATE_INGRESS"],
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).run_confirm_order(confirm_order_request(order_id=order_id, sku="nothing"))
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target, completion_result FROM sys_invocation "
                "WHERE invoked_by_target = 'OrderOrchestrator/" + order_id + "/confirm_order'"
            },
        )
        assert (
            confirm_order_response.outcome
            is relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND
        )
        assert confirm_order_response.reasons == ("no price for sku 'nothing'",)
        assert [
            (row["target"], row["completion_result"]) for row in response.json()["rows"]
        ] == [("OrderActions/price_product", "success")]
