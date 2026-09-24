from __future__ import annotations

import asyncio
import os
import socket
import typing
import urllib.parse as urllib_parse
import uuid

import tesser.testing as ts
import httpx
import hypercorn.asyncio as hypercorn_asyncio
import hypercorn.config as hypercorn_config
import hypercorn.typing as hypercorn_typing
import pytest
import restate
import restate.client as restate_client

import ordering.adapters.activities as activities
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
class FakeUnpricedOrderingApplicationClient(client.OrderingApplicationClient):

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICE_NOT_FOUND,
            prices=(),
            reasons=(f"no price for sku {price_product_request.sku!r}",),
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


@ts.fake
class FakeDecliningPurchaseApplicationClient(client.PurchaseApplicationClient):

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        return relays.TakePaymentResponse(
            outcome=relays.TakePaymentOutcome.DECLINED,
            order_id=take_payment_request.order_id,
            payments=(),
            reasons=(f"the processor declined the charge for order {take_payment_request.order_id!r}",),
        )


@ts.helper
def order_spec(order_id: str = "o1", sku: str = "widget", quantity: int = 2) -> domain.OrderSpec:
    return domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity)


class TestRestateConfirmOrder:

    async def test_confirm_order_calls_price_product_through_the_engine_and_answers_the_total(self) -> None:
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
            async with httpx.AsyncClient(
                base_url=os.environ["RESTATE_INGRESS"], timeout=30.0
            ) as async_client:
                with pytest.raises(restate.HttpError) as foreign:
                    await restate_client.Client(async_client).workflow_call(
                        restate_confirm_order.handler,
                        key="other-" + order_id,
                        arg=relays.ConfirmOrderRequest(order=domain.Order(order_spec(order_id=order_id))),
                    )
                confirm_order_response = await restate_client.Client(async_client).workflow_call(
                    restate_confirm_order.handler,
                    key=order_id,
                    arg=relays.ConfirmOrderRequest(order=domain.Order(order_spec(order_id=order_id, quantity=2))),
                )
            invoked = await admin.post(
                "/query",
                headers={"accept": "application/json"},
                json={
                    "query": "SELECT target, invoked_by_service_name, completion_result "
                    "FROM sys_invocation "
                    f"WHERE invoked_by_target = 'OrderOrchestrator{suffix}/{order_id}/confirm_order'"
                },
            )

            assert foreign.value.status_code == 400
            assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
            assert confirm_order_response.confirmed_orders == (relays.ConfirmedOrder(total_cents=500),)
            assert [
                (row["target"], row["invoked_by_service_name"], row["completion_result"])
                for row in invoked.json()["rows"]
            ] == [(f"OrderActions{suffix}/price_product", f"OrderOrchestrator{suffix}", "success")]
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

    async def test_a_price_the_catalog_does_not_hold_ends_the_workflow_as_an_outcome_not_a_failure(self) -> None:
        suffix = uuid.uuid4().hex
        order_actions_service = restate.Service(f"OrderActions{suffix}")
        purchase_actions_service = restate.Service(f"PurchaseActions{suffix}")
        order_orchestrator_workflow = restate.Workflow(f"OrderOrchestrator{suffix}")
        purchase_orchestrator_workflow = restate.Workflow(f"PurchaseOrchestrator{suffix}")
        restate_price_product = activities.RestatePriceProduct(
            order_actions_service, FakeUnpricedOrderingApplicationClient()
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
            async with httpx.AsyncClient(
                base_url=os.environ["RESTATE_INGRESS"], timeout=30.0
            ) as async_client:
                confirm_order_response = await restate_client.Client(async_client).workflow_call(
                    restate_confirm_order.handler,
                    key=order_id,
                    arg=relays.ConfirmOrderRequest(order=domain.Order(order_spec(order_id=order_id, sku="nothing"))),
                )

            assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND
            assert confirm_order_response.reasons == ("no price for sku 'nothing'",)
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


class TestRestatePayForOrder:

    async def test_pay_for_order_runs_the_order_workflow_keyed_by_the_id_as_it_is_and_then_takes_payment(self) -> None:
        fake_purchase_application_client = FakePurchaseApplicationClient()
        suffix = uuid.uuid4().hex
        order_actions_service = restate.Service(f"OrderActions{suffix}")
        purchase_actions_service = restate.Service(f"PurchaseActions{suffix}")
        order_orchestrator_workflow = restate.Workflow(f"OrderOrchestrator{suffix}")
        purchase_orchestrator_workflow = restate.Workflow(f"PurchaseOrchestrator{suffix}")
        restate_price_product = activities.RestatePriceProduct(
            order_actions_service, FakeOrderingApplicationClient()
        )
        restate_take_payment = activities.RestateTakePayment(
            purchase_actions_service, fake_purchase_application_client
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

            order_id = "../admin?x=1#f-" + str(uuid.uuid4())
            async with httpx.AsyncClient(
                base_url=os.environ["RESTATE_INGRESS"], timeout=30.0
            ) as async_client:
                pay_for_order_response = await restate_client.Client(async_client).workflow_call(
                    restate_pay_for_order.handler,
                    key=urllib_parse.quote(order_id, safe=""),
                    arg=relays.PayForOrderRequest(
                        order=domain.Order(order_spec(order_id=order_id, quantity=2)),
                        payment_method=domain.PaymentMethod("card-4242"),
                    ),
                )
            invoked = await admin.post(
                "/query",
                headers={"accept": "application/json"},
                json={
                    "query": "SELECT target, target_service_key, invoked_by_service_name, completion_result "
                    "FROM sys_invocation "
                    f"WHERE invoked_by_service_name = 'PurchaseOrchestrator{suffix}' ORDER BY created_at"
                },
            )

            assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAID
            assert pay_for_order_response.purchases == (
                relays.Purchase(total_cents=500, payment_reference="pay-" + order_id),
            )
            assert [
                (
                    row["target"],
                    row.get("target_service_key"),
                    row["invoked_by_service_name"],
                    row["completion_result"],
                )
                for row in invoked.json()["rows"]
            ] == [
                (
                    f"OrderOrchestrator{suffix}/{order_id}/confirm_order",
                    order_id,
                    f"PurchaseOrchestrator{suffix}",
                    "success",
                ),
                (f"PurchaseActions{suffix}/take_payment", None, f"PurchaseOrchestrator{suffix}", "success"),
            ]
            assert fake_purchase_application_client.taken == [
                relays.TakePaymentRequest(order_id=order_id, cents=500, payment_method="card-4242")
            ]
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

    async def test_an_order_whose_workflow_already_ran_is_not_paid_for(self) -> None:
        fake_purchase_application_client = FakePurchaseApplicationClient()
        suffix = uuid.uuid4().hex
        order_actions_service = restate.Service(f"OrderActions{suffix}")
        purchase_actions_service = restate.Service(f"PurchaseActions{suffix}")
        order_orchestrator_workflow = restate.Workflow(f"OrderOrchestrator{suffix}")
        purchase_orchestrator_workflow = restate.Workflow(f"PurchaseOrchestrator{suffix}")
        restate_price_product = activities.RestatePriceProduct(
            order_actions_service, FakeOrderingApplicationClient()
        )
        restate_take_payment = activities.RestateTakePayment(
            purchase_actions_service, fake_purchase_application_client
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
            async with httpx.AsyncClient(
                base_url=os.environ["RESTATE_INGRESS"], timeout=30.0
            ) as async_client:
                confirm_order_response = await restate_client.Client(async_client).workflow_call(
                    restate_confirm_order.handler,
                    key=order_id,
                    arg=relays.ConfirmOrderRequest(order=domain.Order(order_spec(order_id=order_id))),
                )
                pay_for_order_response = await restate_client.Client(async_client).workflow_call(
                    restate_pay_for_order.handler,
                    key=order_id,
                    arg=relays.PayForOrderRequest(
                        order=domain.Order(order_spec(order_id=order_id)),
                        payment_method=domain.PaymentMethod("card-4242"),
                    ),
                )

            assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
            assert pay_for_order_response.outcome is relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED
            assert pay_for_order_response.reasons == ("the order was already started",)
            assert fake_purchase_application_client.taken == []
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

    async def test_no_payment_is_taken_for_an_order_that_was_not_confirmed(self) -> None:
        fake_purchase_application_client = FakePurchaseApplicationClient()
        suffix = uuid.uuid4().hex
        order_actions_service = restate.Service(f"OrderActions{suffix}")
        purchase_actions_service = restate.Service(f"PurchaseActions{suffix}")
        order_orchestrator_workflow = restate.Workflow(f"OrderOrchestrator{suffix}")
        purchase_orchestrator_workflow = restate.Workflow(f"PurchaseOrchestrator{suffix}")
        restate_price_product = activities.RestatePriceProduct(
            order_actions_service, FakeUnpricedOrderingApplicationClient()
        )
        restate_take_payment = activities.RestateTakePayment(
            purchase_actions_service, fake_purchase_application_client
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
            async with httpx.AsyncClient(
                base_url=os.environ["RESTATE_INGRESS"], timeout=30.0
            ) as async_client:
                pay_for_order_response = await restate_client.Client(async_client).workflow_call(
                    restate_pay_for_order.handler,
                    key=order_id,
                    arg=relays.PayForOrderRequest(
                        order=domain.Order(order_spec(order_id=order_id, sku="nothing")),
                        payment_method=domain.PaymentMethod("card-4242"),
                    ),
                )

            assert pay_for_order_response.outcome is relays.PayForOrderOutcome.ORDER_NOT_CONFIRMED
            assert pay_for_order_response.reasons == ("no price for sku 'nothing'",)
            assert fake_purchase_application_client.taken == []
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

    async def test_a_declined_charge_ends_the_workflow_as_an_outcome_not_a_failure(self) -> None:
        suffix = uuid.uuid4().hex
        order_actions_service = restate.Service(f"OrderActions{suffix}")
        purchase_actions_service = restate.Service(f"PurchaseActions{suffix}")
        order_orchestrator_workflow = restate.Workflow(f"OrderOrchestrator{suffix}")
        purchase_orchestrator_workflow = restate.Workflow(f"PurchaseOrchestrator{suffix}")
        restate_price_product = activities.RestatePriceProduct(
            order_actions_service, FakeOrderingApplicationClient()
        )
        restate_take_payment = activities.RestateTakePayment(
            purchase_actions_service, FakeDecliningPurchaseApplicationClient()
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
            async with httpx.AsyncClient(
                base_url=os.environ["RESTATE_INGRESS"], timeout=30.0
            ) as async_client:
                with pytest.raises(restate.HttpError) as foreign:
                    await restate_client.Client(async_client).workflow_call(
                        restate_pay_for_order.handler,
                        key="other-" + order_id,
                        arg=relays.PayForOrderRequest(
                            order=domain.Order(order_spec(order_id=order_id)),
                            payment_method=domain.PaymentMethod("card-4242"),
                        ),
                    )
                pay_for_order_response = await restate_client.Client(async_client).workflow_call(
                    restate_pay_for_order.handler,
                    key=order_id,
                    arg=relays.PayForOrderRequest(
                        order=domain.Order(order_spec(order_id=order_id)),
                        payment_method=domain.PaymentMethod("card-4242"),
                    ),
                )

            assert foreign.value.status_code == 400
            assert pay_for_order_response.outcome is relays.PayForOrderOutcome.PAYMENT_DECLINED
            assert pay_for_order_response.reasons == (
                f"the processor declined the charge for order {order_id!r}",
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
