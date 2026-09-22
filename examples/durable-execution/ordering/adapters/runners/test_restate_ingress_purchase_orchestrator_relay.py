from __future__ import annotations

import asyncio
import os
import socket
import uuid

import tesser.testing as ts
import httpx
import pytest

import ordering.adapters.runners as runners
import ordering.application.relays as relays
import ordering.domain as domain


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


class TestRestateIngressPurchaseOrchestratorRelay:

    def test_running_calls_the_workflow_and_answers_with_its_result(self) -> None:
        order_id = str(uuid.uuid4())
        pay_for_order_response = asyncio.run(
            runners.RestateIngressPurchaseOrchestratorRelay(
                os.environ["RESTATE_INGRESS"]
            ).run_pay_for_order(pay_for_order_request(order_id=order_id))
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target, invoked_by, status, completion_result FROM sys_invocation "
                "WHERE target = 'PurchaseOrchestrator/" + order_id + "/pay_for_order'"
            },
        )
        assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAID
        assert pay_for_order_response.order_id == order_id
        assert pay_for_order_response.purchases[0].total_cents == 500
        assert pay_for_order_response.purchases[0].payment_reference == "pay-" + order_id
        assert [
            (row["target"], row["invoked_by"], row["status"], row["completion_result"])
            for row in response.json()["rows"]
        ] == [
            (
                "PurchaseOrchestrator/" + order_id + "/pay_for_order",
                "ingress",
                "completed",
                "success",
            )
        ]

    def test_the_already_invoked_conflict_is_the_outcome_the_engine_crossing_adds(self) -> None:
        order_id = str(uuid.uuid4())
        restate_ingress_purchase_orchestrator_relay = (
            runners.RestateIngressPurchaseOrchestratorRelay(os.environ["RESTATE_INGRESS"])
        )
        first = asyncio.run(
            restate_ingress_purchase_orchestrator_relay.run_pay_for_order(
                pay_for_order_request(order_id=order_id)
            )
        )
        second = asyncio.run(
            restate_ingress_purchase_orchestrator_relay.run_pay_for_order(
                pay_for_order_request(order_id=order_id)
            )
        )
        response = httpx.post(
            os.environ["RESTATE_ADMIN"] + "/query",
            headers={"accept": "application/json"},
            json={
                "query": "SELECT target FROM sys_invocation "
                "WHERE target = 'PurchaseOrchestrator/" + order_id + "/pay_for_order'"
            },
        )
        assert first.outcome is relays.PayForOrderOutcome.PAID
        assert second.outcome is relays.PayForOrderOutcome.ALREADY_STARTED
        assert second.order_id == order_id
        assert second.purchases == ()
        assert second.reasons == ()
        assert [row["target"] for row in response.json()["rows"]] == [
            "PurchaseOrchestrator/" + order_id + "/pay_for_order"
        ]

    def test_an_unreachable_ingress_is_a_fault(self) -> None:
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            unreachable = f"http://127.0.0.1:{closed.getsockname()[1]}"
        with pytest.raises(httpx.TransportError):
            asyncio.run(
                runners.RestateIngressPurchaseOrchestratorRelay(unreachable).run_pay_for_order(
                    pay_for_order_request()
                )
            )
