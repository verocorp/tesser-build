from __future__ import annotations

import pytest

import ordering.application.relays.order_relay as order_relay
import ordering.domain.order as order
import tesser.errors as errors


class TestOrderSnapshot:

    def test_the_snapshot_is_the_orders_canonical_form(self) -> None:
        raw = order_relay.OrderSnapshot().serialize(order.Order(order.OrderSpec(order_id="o1", sku="widget", quantity=2)))
        assert raw == b'{"order_id": "o1", "sku": "widget", "quantity": 2}'

    def test_an_order_comes_back_whole_through_its_own_constructor(self) -> None:
        snapshot = order_relay.OrderSnapshot()
        back = snapshot.deserialize(snapshot.serialize(order.Order(order.OrderSpec(order_id="o7", sku="gadget", quantity=3))))
        assert back.identity == order.OrderId("o7")
        assert back.sku == order.Sku("gadget")
        assert back.quantity == order.Quantity(3)

    def test_a_snapshot_that_breaks_an_invariant_is_refused_on_the_way_in(self) -> None:
        snapshot = order_relay.OrderSnapshot()
        refused = b'{"order_id": "o1", "sku": "widget", "quantity": 0}'
        with pytest.raises(errors.DomainError):
            snapshot.deserialize(refused)
