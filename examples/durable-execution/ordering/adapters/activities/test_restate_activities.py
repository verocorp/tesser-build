from __future__ import annotations

import asyncio
import json
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
import restate.client as restate_client

import ordering.adapters.activities as activities
import ordering.application.client as client
import ordering.application.relays as relays


@ts.fake
class FakeOrderingApplicationClient(client.OrderingApplicationClient):

    def __init__(self) -> None:
        self.priced: list[relays.PriceProductRequest] = []

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        self.priced.append(price_product_request)
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


class TestRestatePriceProduct:

    async def test_restate_serves_price_product_and_a_call_made_with_its_handler_reaches_the_application_client(
        self,
    ) -> None:
        order_actions_service = restate.Service(f"OrderActions{uuid.uuid4().hex}")
        fake_ordering_application_client = FakeOrderingApplicationClient()
        restate_price_product = activities.RestatePriceProduct(
            order_actions_service, fake_ordering_application_client
        )
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([order_actions_service])),
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

            async with httpx.AsyncClient(
                base_url=os.environ["RESTATE_INGRESS"], timeout=30.0
            ) as async_client:
                price_product_response = await restate_client.Client(async_client).service_call(
                    restate_price_product.handler, relays.PriceProductRequest(sku="gadget")
                )

            assert price_product_response == relays.PriceProductResponse(
                outcome=relays.PriceProductOutcome.PRICED,
                prices=(relays.Price(cents=250),),
                reasons=(),
            )
            assert fake_ordering_application_client.priced == [
                relays.PriceProductRequest(sku="gadget")
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


class TestRestateTakePayment:

    async def test_restate_serves_take_payment_and_a_call_made_with_its_handler_reaches_the_application_client(
        self,
    ) -> None:
        purchase_actions_service = restate.Service(f"PurchaseActions{uuid.uuid4().hex}")
        fake_purchase_application_client = FakePurchaseApplicationClient()
        restate_take_payment = activities.RestateTakePayment(
            purchase_actions_service, fake_purchase_application_client
        )
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([purchase_actions_service])),
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

            async with httpx.AsyncClient(
                base_url=os.environ["RESTATE_INGRESS"], timeout=30.0
            ) as async_client:
                take_payment_response = await restate_client.Client(async_client).service_call(
                    restate_take_payment.handler,
                    relays.TakePaymentRequest(order_id="o1", cents=750, payment_method="card-4242"),
                )

            assert take_payment_response.outcome is relays.TakePaymentOutcome.TAKEN
            assert take_payment_response.payments == (relays.Payment(reference="pay-o1", cents=750),)
            assert fake_purchase_application_client.taken == [
                relays.TakePaymentRequest(order_id="o1", cents=750, payment_method="card-4242")
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


class TestRestateEngineRefusals:

    async def test_a_body_the_snapshot_cannot_read_is_a_terminal_500_that_is_not_retried(self) -> None:
        order_actions_service = restate.Service(f"OrderActions{uuid.uuid4().hex}")
        restate_price_product = activities.RestatePriceProduct(order_actions_service, FakeOrderingApplicationClient())
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([order_actions_service])),
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

            async with httpx.AsyncClient(base_url=os.environ["RESTATE_INGRESS"], timeout=30.0) as async_client:
                with pytest.raises(restate.HttpError) as refused:
                    await restate_client.Client(async_client).generic_call(
                        order_actions_service.name, restate_price_product.handler.__name__,
                        b"[1, 2]",
                        headers={"content-type": "application/json"},
                    )

            assert refused.value.status_code == 500
            assert json.loads(refused.value.body or "")["message"].startswith("Unable to parse an input argument.")
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)

    async def test_the_ingress_refuses_a_call_to_an_ingress_private_actions_service(self) -> None:
        order_actions_service = restate.Service(f"OrderActions{uuid.uuid4().hex}", ingress_private=True)
        restate_price_product = activities.RestatePriceProduct(order_actions_service, FakeOrderingApplicationClient())
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([order_actions_service])),
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

            async with httpx.AsyncClient(base_url=os.environ["RESTATE_INGRESS"], timeout=30.0) as async_client:
                with pytest.raises(restate.HttpError) as refused:
                    await restate_client.Client(async_client).service_call(restate_price_product.handler, relays.PriceProductRequest(sku="gadget"))

            assert refused.value.status_code == 400
            assert json.loads(refused.value.body or "")["message"] == "the invoked service is not public"
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)
