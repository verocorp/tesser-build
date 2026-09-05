from __future__ import annotations

import asyncio

import pytest

import ordering.client.client as client
import ordering.component.component as component
import ordering.component.config as config
import tesser.errors as errors


class TestOrderingContext:

    def test_placing_an_order_with_no_ingress_is_an_infra_error(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://127.0.0.1:9")))
        try:
            with pytest.raises(errors.InfraError):
                asyncio.run(
                    wired.client.place(
                        client.PlaceRequest(order_id="o1", sku="widget", quantity=2, note="gift")
                    )
                )
        finally:
            wired.close()
