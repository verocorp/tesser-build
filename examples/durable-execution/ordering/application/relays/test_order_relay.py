from __future__ import annotations

import pytest

import ordering.application.relays.order_relay as order_relay
import ordering.domain.order as order
import tesser.errors as errors


class TestOrderSnapshot:

    def test_the_snapshot_is_the_orders_canonical_form(self) -> None:
        placed = order.Order(order.OrderSpec(order_id="o1", sku="widget", quantity=2))
        assert order_relay.OrderSnapshot().serialize(placed) == b'{"order_id": "o1", "sku": "widget", "quantity": 2}'

    def test_an_order_comes_back_whole_through_its_own_constructor(self) -> None:
        snapshot = order_relay.OrderSnapshot()
        placed = order.Order(order.OrderSpec(order_id="o7", sku="gadget", quantity=3))
        back = snapshot.deserialize(snapshot.serialize(placed))
        assert back.identity == order.OrderId("o7")
        assert back.sku == order.Sku("gadget")
        assert back.quantity == order.Quantity(3)

    def test_a_snapshot_that_breaks_an_invariant_is_refused_on_the_way_in(self) -> None:
        with pytest.raises(errors.DomainError):
            order_relay.OrderSnapshot().deserialize(b'{"order_id": "o1", "sku": "widget", "quantity": 0}')


class TestStartRequestSnapshot:

    def test_a_start_request_is_the_order_it_carries_and_nothing_more(self) -> None:
        placed = order.Order(order.OrderSpec(order_id="o1", sku="widget", quantity=2))
        raw = order_relay.StartRequestSnapshot().serialize(order_relay.StartRequest(order=placed))
        assert raw == b'{"order_id": "o1", "sku": "widget", "quantity": 2}'

    def test_a_start_request_comes_back_around_its_order(self) -> None:
        snapshot = order_relay.StartRequestSnapshot()
        placed = order.Order(order.OrderSpec(order_id="o7", sku="gadget", quantity=3))
        back = snapshot.deserialize(snapshot.serialize(order_relay.StartRequest(order=placed)))
        assert back.order.identity == order.OrderId("o7")
        assert back.order.sku == order.Sku("gadget")
        assert back.order.quantity == order.Quantity(3)


class TestQuoteRequestSnapshot:

    def test_a_quote_request_is_its_sku(self) -> None:
        raw = order_relay.QuoteRequestSnapshot().serialize(order_relay.QuoteRequest(sku="widget"))
        assert raw == b'{"sku": "widget"}'

    def test_a_quote_request_comes_back_equal(self) -> None:
        snapshot = order_relay.QuoteRequestSnapshot()
        asked = order_relay.QuoteRequest(sku="gadget")
        assert snapshot.deserialize(snapshot.serialize(asked)) == asked


class TestQuoteResponseSnapshot:

    def test_a_quote_response_is_its_cents(self) -> None:
        raw = order_relay.QuoteResponseSnapshot().serialize(order_relay.QuoteResponse(cents=250))
        assert raw == b'{"cents": 250}'

    def test_a_quote_response_comes_back_equal(self) -> None:
        snapshot = order_relay.QuoteResponseSnapshot()
        answered = order_relay.QuoteResponse(cents=250)
        assert snapshot.deserialize(snapshot.serialize(answered)) == answered


class TestRunResponseSnapshot:

    def test_a_run_response_is_the_order_id_and_the_total(self) -> None:
        ran = order_relay.RunResponse(order_id="o1", total_cents=500)
        assert order_relay.RunResponseSnapshot().serialize(ran) == b'{"order_id": "o1", "total_cents": 500}'

    def test_a_run_response_comes_back_equal(self) -> None:
        snapshot = order_relay.RunResponseSnapshot()
        ran = order_relay.RunResponse(order_id="o7", total_cents=750)
        assert snapshot.deserialize(snapshot.serialize(ran)) == ran
