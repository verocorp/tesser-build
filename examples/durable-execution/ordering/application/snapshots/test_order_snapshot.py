from __future__ import annotations

import pytest

import ordering.application.snapshots as snapshots
import ordering.domain as domain
import ordering.application.ports as ports


class TestOrderSnapshot:

    def test_the_snapshot_is_the_orders_canonical_form(self) -> None:
        order = domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=2))
        assert snapshots.OrderSnapshot().serialize(order) == b'{"order_id": "o1", "sku": "widget", "quantity": 2}'

    def test_an_order_comes_back_whole_through_its_own_constructor(self) -> None:
        order_snapshot = snapshots.OrderSnapshot()
        order = domain.Order(domain.OrderSpec(order_id="o7", sku="gadget", quantity=3))
        back = order_snapshot.deserialize(order_snapshot.serialize(order))
        assert back.identity == domain.OrderId("o7")
        assert back.sku == domain.Sku("gadget")
        assert back.quantity == domain.Quantity(3)

    def test_a_snapshot_that_breaks_an_invariant_is_refused_on_the_way_in(self) -> None:
        with pytest.raises(ports.EngineRejected):
            snapshots.OrderSnapshot().deserialize(b'{"order_id": "o1", "sku": "widget", "quantity": 0}')

    def test_a_snapshot_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"order_id": "o1", "sku": [1, 2], "quantity": 2}',
            b'{"order_id": "o1", "sku": "widget", "quantity": true}',
            b'{"order_id": "o1", "sku": "widget", "quantity": "2"}',
            b'{"order_id": "o1", "sku": "widget"}',
            b'["o1", "widget", 2]',
        ):
            with pytest.raises(ports.EngineRejected):
                snapshots.OrderSnapshot().deserialize(raw)
