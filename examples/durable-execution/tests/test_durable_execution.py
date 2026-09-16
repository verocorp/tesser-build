from __future__ import annotations

import asyncio
import uuid

import pytest

import app as app
import ordering.client as ordering_client


class TestWiredApp:

    def test_the_loaded_app_holds_the_restate_runtime_the_host_mounts(self) -> None:
        durable_execution_app = app.load()
        try:
            declared = [
                durable_execution_app.ordering.restate_order_runtime.order_actions_service.name,
                durable_execution_app.ordering.restate_order_runtime.order_orchestrator_workflow.name,
            ]
        finally:
            durable_execution_app.close()
        assert declared == ["OrderActions", "OrderOrchestrator"]

    def test_the_loaded_app_places_an_order_through_the_engine(self) -> None:
        order_id = str(uuid.uuid4())
        durable_execution_app = app.load()
        try:
            place_order_response = asyncio.run(
                durable_execution_app.ordering.client.place_order(
                    ordering_client.PlaceOrderRequest(order_id=order_id, sku="gadget", quantity=3)
                )
            )
        finally:
            durable_execution_app.close()
        assert place_order_response.order_id == order_id
        assert place_order_response.total_cents == 3000

    def test_the_loaded_app_pays_for_an_order_through_the_engine(self) -> None:
        order_id = str(uuid.uuid4())
        durable_execution_app = app.load()
        try:
            make_order_payment_response = asyncio.run(
                durable_execution_app.ordering.client.make_order_payment(
                    ordering_client.MakeOrderPaymentRequest(
                        order_id=order_id, sku="widget", quantity=2, payment_method="card-4242"
                    )
                )
            )
        finally:
            durable_execution_app.close()
        assert make_order_payment_response.order_id == order_id
        assert make_order_payment_response.total_cents == 500
        assert make_order_payment_response.payment_reference == "pay-" + order_id

    def test_each_declared_situation_reaches_the_caller_as_its_own_error(self) -> None:
        placed = str(uuid.uuid4())
        durable_execution_app = app.load()
        try:
            asyncio.run(
                durable_execution_app.ordering.client.place_order(
                    ordering_client.PlaceOrderRequest(order_id=placed, sku="widget", quantity=1)
                )
            )
            with pytest.raises(ordering_client.OrderAlreadyStarted):
                asyncio.run(
                    durable_execution_app.ordering.client.place_order(
                        ordering_client.PlaceOrderRequest(order_id=placed, sku="widget", quantity=1)
                    )
                )
            with pytest.raises(ordering_client.OrderNotConfirmed):
                asyncio.run(
                    durable_execution_app.ordering.client.make_order_payment(
                        ordering_client.MakeOrderPaymentRequest(
                            order_id=placed, sku="widget", quantity=1, payment_method="card-4242"
                        )
                    )
                )
            with pytest.raises(ordering_client.ProductPriceNotFound):
                asyncio.run(
                    durable_execution_app.ordering.client.place_order(
                        ordering_client.PlaceOrderRequest(
                            order_id=str(uuid.uuid4()), sku="nothing", quantity=1
                        )
                    )
                )
            with pytest.raises(ordering_client.PaymentDeclined):
                asyncio.run(
                    durable_execution_app.ordering.client.make_order_payment(
                        ordering_client.MakeOrderPaymentRequest(
                            order_id=str(uuid.uuid4()),
                            sku="widget",
                            quantity=1,
                            payment_method="declined",
                        )
                    )
                )
        finally:
            durable_execution_app.close()
