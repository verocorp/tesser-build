from __future__ import annotations

import asyncio

import pytest

import ordering.client as client
import ordering.component as component
import tesser.errors as errors


class TestOrderingContext:

    def test_placing_an_order_with_no_ingress_is_an_infra_error(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://127.0.0.1:9")))
        try:
            with pytest.raises(errors.InfraError):
                asyncio.run(
                    ordering.client.place_order(
                        client.PlaceOrderRequest(
                            order_id="o1", sku="widget", quantity=2, note="gift"
                        )
                    )
                )
        finally:
            ordering.close()
