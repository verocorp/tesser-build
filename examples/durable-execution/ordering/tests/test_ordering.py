from __future__ import annotations

import asyncio

import pytest

import ordering.client as client
import ordering.component as component


class TestOrderingContext:

    def test_submitting_an_order_with_no_ingress_is_unavailable(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://127.0.0.1:9")))
        try:
            with pytest.raises(client.Unavailable):
                asyncio.run(
                    ordering.client.submit_order(
                        client.SubmitOrderRequest(order_id="o1", sku="widget", quantity=2)
                    )
                )
        finally:
            ordering.close()

    def test_placing_an_order_with_no_ingress_is_unavailable(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://127.0.0.1:9")))
        try:
            with pytest.raises(client.Unavailable):
                asyncio.run(
                    ordering.client.place_order(
                        client.PlaceOrderRequest(order_id="o1", sku="widget", quantity=2)
                    )
                )
        finally:
            ordering.close()

    def test_purchasing_with_no_ingress_is_unavailable(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://127.0.0.1:9")))
        try:
            with pytest.raises(client.Unavailable):
                asyncio.run(
                    ordering.client.purchase(
                        client.PurchaseRequest(order_id="o1", sku="widget", quantity=2)
                    )
                )
        finally:
            ordering.close()
