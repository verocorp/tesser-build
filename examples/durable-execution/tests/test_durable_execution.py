from __future__ import annotations

import asyncio

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

    def test_submitting_an_order_with_no_ingress_is_unavailable(self) -> None:
        durable_execution_app = app.load()
        try:
            with pytest.raises(ordering_client.Unavailable):
                asyncio.run(
                    durable_execution_app.ordering.client.submit_order(
                        ordering_client.SubmitOrderRequest(order_id="o1", sku="widget", quantity=2)
                    )
                )
        finally:
            durable_execution_app.close()
