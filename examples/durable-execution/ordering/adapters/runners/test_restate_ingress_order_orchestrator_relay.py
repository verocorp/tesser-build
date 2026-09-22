from __future__ import annotations

import asyncio
import os
import socket
import uuid

import tesser.testing as ts
import httpx
import pytest

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


class TestRestateIngressOrderOrchestratorRelayStarting:

    def test_starting_sends_the_workflow_keyed_by_the_orders_id(self) -> None:
        order_id = str(uuid.uuid4())
        start_confirm_order_response = asyncio.run(
            runners.RestateIngressOrderOrchestratorRelay(
                os.environ["RESTATE_INGRESS"],
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).start_confirm_order(confirm_order_request(order_id=order_id))
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target, target_service_key, invoked_by FROM sys_invocation "
                "WHERE target_service_key = '" + order_id + "'"
            },
        )
        assert (
            start_confirm_order_response.outcome is relays.StartConfirmOrderOutcome.STARTED
        )
        assert start_confirm_order_response.order_id == order_id
        assert [
            (row["target"], row["target_service_key"], row["invoked_by"])
            for row in response.json()["rows"]
        ] == [("OrderOrchestrator/" + order_id + "/confirm_order", order_id, "ingress")]

    def test_the_key_is_encoded_so_an_order_id_cannot_reshape_the_path(self) -> None:
        order_id = "../admin?x=1#f-" + str(uuid.uuid4())
        start_confirm_order_response = asyncio.run(
            runners.RestateIngressOrderOrchestratorRelay(
                os.environ["RESTATE_INGRESS"],
                runtimes.RestateOrderRuntime(
                    FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                ),
            ).start_confirm_order(confirm_order_request(order_id=order_id))
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target, target_service_key FROM sys_invocation "
                "WHERE target_service_key = '" + order_id + "'"
            },
        )
        assert start_confirm_order_response.order_id == order_id
        assert [
            (row["target"], row["target_service_key"]) for row in response.json()["rows"]
        ] == [("OrderOrchestrator/" + order_id + "/confirm_order", order_id)]

    def test_a_repeat_send_is_accepted_and_the_engine_runs_the_workflow_once(self) -> None:
        order_id = str(uuid.uuid4())
        restate_ingress_order_orchestrator_relay = runners.RestateIngressOrderOrchestratorRelay(
            os.environ["RESTATE_INGRESS"],
            runtimes.RestateOrderRuntime(
                FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
            ),
        )
        first = asyncio.run(
            restate_ingress_order_orchestrator_relay.start_confirm_order(
                confirm_order_request(order_id=order_id)
            )
        )
        second = asyncio.run(
            restate_ingress_order_orchestrator_relay.start_confirm_order(
                confirm_order_request(order_id=order_id)
            )
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target FROM sys_invocation "
                "WHERE target_service_key = '" + order_id + "'"
            },
        )
        assert first.outcome is relays.StartConfirmOrderOutcome.STARTED
        assert second.outcome is relays.StartConfirmOrderOutcome.STARTED
        assert [row["target"] for row in response.json()["rows"]] == [
            "OrderOrchestrator/" + order_id + "/confirm_order"
        ]

    def test_an_unreachable_ingress_is_a_fault(self) -> None:
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            unreachable = f"http://127.0.0.1:{closed.getsockname()[1]}"
        with pytest.raises(httpx.TransportError):
            asyncio.run(
                runners.RestateIngressOrderOrchestratorRelay(
                    unreachable,
                    runtimes.RestateOrderRuntime(
                        FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                    ),
                ).start_confirm_order(confirm_order_request())
            )


class TestRestateIngressOrderOrchestratorRelayRunning:

    def test_running_calls_the_workflow_and_answers_with_its_result(self) -> None:
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
                "query": "SELECT target, status, completion_result FROM sys_invocation "
                "WHERE target_service_key = '" + order_id + "'"
            },
        )
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
        assert confirm_order_response.order_id == order_id
        assert confirm_order_response.confirmed_orders[0].total_cents == 500
        assert [
            (row["target"], row["status"], row["completion_result"])
            for row in response.json()["rows"]
        ] == [("OrderOrchestrator/" + order_id + "/confirm_order", "completed", "success")]

    def test_the_already_invoked_conflict_is_the_outcome_the_engine_crossing_adds(self) -> None:
        order_id = str(uuid.uuid4())
        restate_ingress_order_orchestrator_relay = runners.RestateIngressOrderOrchestratorRelay(
            os.environ["RESTATE_INGRESS"],
            runtimes.RestateOrderRuntime(
                FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
            ),
        )
        first = asyncio.run(
            restate_ingress_order_orchestrator_relay.run_confirm_order(
                confirm_order_request(order_id=order_id)
            )
        )
        second = asyncio.run(
            restate_ingress_order_orchestrator_relay.run_confirm_order(
                confirm_order_request(order_id=order_id)
            )
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target FROM sys_invocation "
                "WHERE target_service_key = '" + order_id + "'"
            },
        )
        assert first.outcome is relays.ConfirmOrderOutcome.CONFIRMED
        assert second.outcome is relays.ConfirmOrderOutcome.ALREADY_STARTED
        assert second.order_id == order_id
        assert second.confirmed_orders == ()
        assert second.reasons == ()
        assert [row["target"] for row in response.json()["rows"]] == [
            "OrderOrchestrator/" + order_id + "/confirm_order"
        ]

    def test_an_unreachable_ingress_is_a_fault_when_running(self) -> None:
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            unreachable = f"http://127.0.0.1:{closed.getsockname()[1]}"
        with pytest.raises(httpx.TransportError):
            asyncio.run(
                runners.RestateIngressOrderOrchestratorRelay(
                    unreachable,
                    runtimes.RestateOrderRuntime(
                        FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                    ),
                ).run_confirm_order(confirm_order_request())
            )
