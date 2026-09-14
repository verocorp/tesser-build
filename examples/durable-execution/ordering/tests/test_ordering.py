from __future__ import annotations

import asyncio

import pytest

import ordering.client as client
import ordering.component as component


class TestOrderingContext:

    def test_submitting_an_order_with_no_ingress_is_a_fault(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://127.0.0.1:9")))
        try:
            with pytest.raises(Exception) as excinfo:
                asyncio.run(
                    ordering.client.submit_order(
                        client.SubmitOrderRequest(order_id="o1", sku="widget", quantity=2)
                    )
                )
            assert not isinstance(excinfo.value, client.ERRORS)
        finally:
            ordering.close()

    def test_placing_an_order_with_no_ingress_is_a_fault(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://127.0.0.1:9")))
        try:
            with pytest.raises(Exception) as excinfo:
                asyncio.run(
                    ordering.client.place_order(
                        client.PlaceOrderRequest(order_id="o1", sku="widget", quantity=2)
                    )
                )
            assert not isinstance(excinfo.value, client.ERRORS)
        finally:
            ordering.close()

    def test_paying_for_an_order_with_no_ingress_is_a_fault(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://127.0.0.1:9")))
        try:
            with pytest.raises(Exception) as excinfo:
                asyncio.run(
                    ordering.client.make_order_payment(
                        client.MakeOrderPaymentRequest(
                            order_id="o1", sku="widget", quantity=2, payment_method="card-4242"
                        )
                    )
                )
            assert not isinstance(excinfo.value, client.ERRORS)
        finally:
            ordering.close()

    def test_an_order_the_domain_refuses_is_the_situation_of_that_name(self) -> None:
        ordering = component.Ordering(component.Config(component.Spec(ingress="http://127.0.0.1:9")))
        try:
            with pytest.raises(client.OrderRejected):
                asyncio.run(
                    ordering.client.place_order(
                        client.PlaceOrderRequest(order_id="o1", sku="widget", quantity=0)
                    )
                )
        finally:
            ordering.close()
