from __future__ import annotations

import pytest

import ordering.application.relays as relays
import ordering.domain as domain


class TestPayForOrderRequestSnapshot:

    def test_a_request_is_the_order_it_carries_and_the_payment_method(self) -> None:
        order = domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=2))
        raw = relays.PayForOrderRequestSnapshot().serialize(
            relays.PayForOrderRequest(
                order=order, payment_method=domain.PaymentMethod("card-4242")
            )
        )
        assert raw == (
            b'{"order": {"order_id": "o1", "sku": "widget", "quantity": 2}, '
            b'"payment_method": "card-4242"}'
        )

    def test_a_request_comes_back_around_its_order_and_method(self) -> None:
        pay_for_order_request_snapshot = relays.PayForOrderRequestSnapshot()
        order = domain.Order(domain.OrderSpec(order_id="o7", sku="gadget", quantity=3))
        pay_for_order_request = pay_for_order_request_snapshot.deserialize(
            pay_for_order_request_snapshot.serialize(
                relays.PayForOrderRequest(
                    order=order, payment_method=domain.PaymentMethod("card-1234")
                )
            )
        )
        assert pay_for_order_request.order.identity == domain.OrderId("o7")
        assert pay_for_order_request.order.sku == domain.Sku("gadget")
        assert pay_for_order_request.order.quantity == domain.Quantity(3)
        assert pay_for_order_request.payment_method == domain.PaymentMethod("card-1234")

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"order": {"order_id": "o1", "sku": "widget", "quantity": 2}}',
            b'{"order": {"order_id": "o1", "sku": "widget", "quantity": 2}, "payment_method": ""}',
            b'{"order": {"order_id": "o1", "sku": "widget", "quantity": 2}, "payment_method": 7}',
            b'{"payment_method": "card-4242"}',
            b'{"order": {"order_id": "o1", "sku": "widget", "quantity": 0}, "payment_method": "card-4242"}',
            b'["o1", "card-4242"]',
        ):
            with pytest.raises(ValueError):
                relays.PayForOrderRequestSnapshot().deserialize(raw)


class TestPayForOrderResponseSnapshot:

    def test_a_paid_response_is_its_outcome_the_order_and_the_one_purchase(self) -> None:
        pay_for_order_response = relays.PayForOrderResponse(
            outcome=relays.PayForOrderOutcome.PAID,
            order_id="o1",
            purchases=(relays.Purchase(total_cents=500, payment_reference="pay-o1"),),
            reasons=(),
        )
        assert relays.PayForOrderResponseSnapshot().serialize(pay_for_order_response) == (
            b'{"outcome": "paid", "order_id": "o1", '
            b'"purchases": [{"total_cents": 500, "payment_reference": "pay-o1"}], "reasons": []}'
        )

    def test_an_unpaid_response_carries_no_purchase_and_its_reason(self) -> None:
        pay_for_order_response = relays.PayForOrderResponse(
            outcome=relays.PayForOrderOutcome.PAYMENT_DECLINED,
            order_id="o1",
            purchases=(),
            reasons=("the processor declined the charge",),
        )
        assert relays.PayForOrderResponseSnapshot().serialize(pay_for_order_response) == (
            b'{"outcome": "payment_declined", "order_id": "o1", "purchases": [], '
            b'"reasons": ["the processor declined the charge"]}'
        )

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"outcome": "paid", "order_id": "o1", "purchases": []}',
            b'{"outcome": "paid", "order_id": "", "purchases": [], "reasons": []}',
            b'{"outcome": "paid", "order_id": "o1", "purchases": [{"total_cents": 500, "payment_reference": ""}], "reasons": []}',
            b'{"outcome": "paid", "order_id": "o1", "purchases": [{"total_cents": -1, "payment_reference": "pay-o1"}], "reasons": []}',
            b'{"outcome": "paid", "order_id": "o1", "purchases": [{"total_cents": true, "payment_reference": "pay-o1"}], "reasons": []}',
            b'{"outcome": "paid", "order_id": "o1", "purchases": [{"total_cents": "500", "payment_reference": "pay-o1"}], "reasons": []}',
            b'{"outcome": "paid", "order_id": "o1", "purchases": [{"total_cents": 500, "payment_reference": 7}], "reasons": []}',
            b'{"outcome": "paid", "order_id": {}, "purchases": [], "reasons": []}',
            b'{"outcome": "paid", "order_id": "o1", "purchases": [], "reasons": []}',
            b'{"outcome": "payment_declined", "order_id": "o1", "purchases": [{"total_cents": 500, "payment_reference": "pay-o1"}], "reasons": []}',
            b'{"outcome": "settled", "order_id": "o1", "purchases": [], "reasons": []}',
            b'["o1", 500, "pay-o1"]',
        ):
            with pytest.raises(ValueError):
                relays.PayForOrderResponseSnapshot().deserialize(raw)

    def test_a_response_comes_back_equal(self) -> None:
        pay_for_order_response_snapshot = relays.PayForOrderResponseSnapshot()
        pay_for_order_response = relays.PayForOrderResponse(
            outcome=relays.PayForOrderOutcome.PAID,
            order_id="o7",
            purchases=(relays.Purchase(total_cents=750, payment_reference="pay-o7"),),
            reasons=(),
        )
        assert pay_for_order_response_snapshot.deserialize(
            pay_for_order_response_snapshot.serialize(pay_for_order_response)
        ) == pay_for_order_response
