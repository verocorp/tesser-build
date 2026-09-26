from __future__ import annotations

import pytest

import ordering.application.relays as relays
import ordering.domain as domain


class TestConfirmOrderRequestSnapshot:

    def test_a_request_is_the_order_it_carries_and_nothing_more(self) -> None:
        order = domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=2))
        raw = relays.ConfirmOrderRequestSnapshot().serialize(
            relays.ConfirmOrderRequest(order=order)
        )
        assert raw == b'{"order_id": "o1", "sku": "widget", "quantity": 2}'

    def test_a_request_comes_back_around_its_order(self) -> None:
        confirm_order_request_snapshot = relays.ConfirmOrderRequestSnapshot()
        order = domain.Order(domain.OrderSpec(order_id="o7", sku="gadget", quantity=3))
        confirm_order_request = confirm_order_request_snapshot.deserialize(
            confirm_order_request_snapshot.serialize(relays.ConfirmOrderRequest(order=order))
        )
        assert confirm_order_request.order.identity == domain.OrderId("o7")
        assert confirm_order_request.order.sku == domain.Sku("gadget")
        assert confirm_order_request.order.quantity == domain.Quantity(3)


class TestConfirmOrderResponseSnapshot:

    def test_a_confirmation_cannot_contradict_its_total(self) -> None:
        for raw in (
            b'{"outcome": "confirmed", "order_id": "o1", "confirmed_orders": [], "reasons": []}',
            b'{"outcome": "confirmed", "order_id": "o1", "confirmed_orders": [{"total_cents": 750}, {"total_cents": 800}], "reasons": []}',
            b'{"outcome": "product_price_not_found", "order_id": "o1", "confirmed_orders": [{"total_cents": 750}], "reasons": ["missing"]}',
            b'{"outcome": "already_started", "order_id": "o1", "confirmed_orders": [{"total_cents": 750}], "reasons": []}',
        ):
            with pytest.raises(ValueError):
                relays.ConfirmOrderResponseSnapshot().deserialize(raw)

    def test_a_previously_started_confirmation_carries_no_payable_order(self) -> None:
        confirm_order_response = relays.ConfirmOrderResponseSnapshot().deserialize(
            b'{"outcome": "already_started", "order_id": "o1", "confirmed_orders": [], "reasons": []}'
        )
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.ALREADY_STARTED
        assert confirm_order_response.confirmed_orders == ()

    def test_an_unknown_confirmation_status_is_refused(self) -> None:
        with pytest.raises(ValueError):
            relays.ConfirmOrderResponseSnapshot().deserialize(
                b'{"outcome": "unknown", "order_id": "o1", "confirmed_orders": [], "reasons": []}'
            )

    def test_a_confirmed_response_is_its_outcome_the_order_id_and_the_total(self) -> None:
        confirm_order_response = relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id="o1",
            confirmed_orders=(relays.ConfirmedOrder(total_cents=500),),
            reasons=(),
        )
        assert relays.ConfirmOrderResponseSnapshot().serialize(confirm_order_response) == (
            b'{"outcome": "confirmed", "order_id": "o1", '
            b'"confirmed_orders": [{"total_cents": 500}], "reasons": []}'
        )

    def test_an_unconfirmed_response_carries_no_order_and_its_reason(self) -> None:
        confirm_order_response = relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND,
            order_id="o1",
            confirmed_orders=(),
            reasons=("no price for sku 'nope'",),
        )
        assert relays.ConfirmOrderResponseSnapshot().serialize(confirm_order_response) == (
            b'{"outcome": "product_price_not_found", "order_id": "o1", '
            b'"confirmed_orders": [], "reasons": ["no price for sku \'nope\'"]}'
        )

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"outcome": "confirmed", "order_id": "o1"}',
            b'{"outcome": "confirmed", "order_id": "", "confirmed_orders": [], "reasons": []}',
            b'{"outcome": "confirmed", "order_id": "o1", "confirmed_orders": [{"total_cents": -1}], "reasons": []}',
            b'{"outcome": "confirmed", "order_id": "o1", "confirmed_orders": [{"total_cents": true}], "reasons": []}',
            b'{"outcome": "confirmed", "order_id": "o1", "confirmed_orders": [{"total_cents": NaN}], "reasons": []}',
            b'{"outcome": "confirmed", "order_id": "o1", "confirmed_orders": [{"total_cents": "500"}], "reasons": []}',
            b'{"outcome": "confirmed", "order_id": {}, "confirmed_orders": [], "reasons": []}',
            b'{"outcome": "unconfirmed", "order_id": "o1", "confirmed_orders": [], "reasons": []}',
            b'["o1", 500]',
        ):
            with pytest.raises(ValueError):
                relays.ConfirmOrderResponseSnapshot().deserialize(raw)

    def test_a_response_comes_back_equal(self) -> None:
        confirm_order_response_snapshot = relays.ConfirmOrderResponseSnapshot()
        confirm_order_response = relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id="o7",
            confirmed_orders=(relays.ConfirmedOrder(total_cents=750),),
            reasons=(),
        )
        assert confirm_order_response_snapshot.deserialize(
            confirm_order_response_snapshot.serialize(confirm_order_response)
        ) == confirm_order_response
