from __future__ import annotations

import asyncio

import pytest

import app.loader as loader
import ordering.client.client as client
import tesser.errors as errors


class TestWiredApp:

    def test_the_loaded_app_declares_the_restate_definitions_the_host_mounts(self) -> None:
        app = loader.load()
        try:
            declared = [d.name for job in app.ordering.jobs for d in job.definitions()]
        finally:
            app.close()
        assert declared == ["OrderingActions", "Ordering"]

    def test_placing_an_order_with_no_ingress_is_an_infra_error(self) -> None:
        app = loader.load()
        try:
            with pytest.raises(errors.InfraError):
                asyncio.run(
                    app.ordering.client.place(
                        client.PlaceRequest(order_id="o1", sku="widget", quantity=2)
                    )
                )
        finally:
            app.close()
