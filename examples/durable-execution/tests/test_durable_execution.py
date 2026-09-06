from __future__ import annotations

import asyncio

import pytest

import app as app
import ordering.client as client
import tesser.errors as errors


class TestWiredApp:

    def test_the_loaded_app_declares_the_restate_definitions_the_host_mounts(self) -> None:
        durable_execution_app = app.load()
        try:
            declared = [
                d.name for job in durable_execution_app.ordering.jobs for d in job.definitions()
            ]
        finally:
            durable_execution_app.close()
        assert declared == ["OrderingActions", "Ordering"]

    def test_placing_an_order_with_no_ingress_is_an_infra_error(self) -> None:
        durable_execution_app = app.load()
        try:
            with pytest.raises(errors.InfraError):
                asyncio.run(
                    durable_execution_app.ordering.client.place(
                        client.PlaceRequest(order_id="o1", sku="widget", quantity=2)
                    )
                )
        finally:
            durable_execution_app.close()
