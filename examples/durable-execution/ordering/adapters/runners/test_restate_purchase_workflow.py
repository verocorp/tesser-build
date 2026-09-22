from __future__ import annotations

import asyncio
import os
import uuid

import tesser.testing as ts
import httpx

import ordering.adapters.runners as runners
import ordering.application.relays as relays
import ordering.domain as domain


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
                os.environ["RESTATE_INGRESS"]
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
                os.environ["RESTATE_INGRESS"]
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
        assert [(row["target"], row["target_service_key"]) for row in response.json()["rows"]] == [
            ("OrderOrchestrator/" + order_id + "/confirm_order", order_id)
        ]

    def test_the_already_invoked_conflict_is_the_outcome_the_engine_crossing_adds(self) -> None:
        order_id = str(uuid.uuid4())
        confirm_order_response = asyncio.run(
            runners.RestateIngressOrderOrchestratorRelay(
                os.environ["RESTATE_INGRESS"]
            ).run_confirm_order(confirm_order_request(order_id=order_id))
        )
        pay_for_order_response = asyncio.run(
            runners.RestateIngressPurchaseOrchestratorRelay(
                os.environ["RESTATE_INGRESS"]
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


class TestRestateInvocationPurchaseActionsRelay:

    def test_running_take_payment_journals_a_call_to_the_runtimes_handler(self) -> None:
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
                os.environ["RESTATE_INGRESS"]
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
                os.environ["RESTATE_INGRESS"]
            ).run_pay_for_order(pay_for_order_request(order_id=order_id, payment_method="declined"))
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
        assert [(row["target"], row["completion_result"]) for row in response.json()["rows"]] == [
            ("PurchaseActions/take_payment", "success")
        ]
