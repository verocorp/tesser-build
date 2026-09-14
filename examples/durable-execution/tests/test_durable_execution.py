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

    def test_an_engine_that_does_not_answer_is_a_fault_and_no_declared_situation(self) -> None:
        durable_execution_app = app.load()
        try:
            with pytest.raises(Exception) as excinfo:
                asyncio.run(
                    durable_execution_app.ordering.client.submit_order(
                        ordering_client.SubmitOrderRequest(order_id="o1", sku="widget", quantity=2)
                    )
                )
            assert not isinstance(excinfo.value, ordering_client.ERRORS)
        finally:
            durable_execution_app.close()
