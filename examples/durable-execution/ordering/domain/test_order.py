from __future__ import annotations

import pytest

import ordering.domain as domain
import tesser.errors as errors


class TestOrder:

    def test_an_order_constructs_from_its_spec(self) -> None:
        order_spec = domain.OrderSpec(order_id="o1", sku="widget", quantity=2)
        order = domain.Order(order_spec)
        assert str(order.identity) == order_spec.order_id
        assert str(order.sku) == order_spec.sku
        assert int(order.quantity) == order_spec.quantity

    def test_the_total_is_the_unit_price_times_the_quantity(self) -> None:
        order = domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=3))
        assert order.total(domain.PriceSpec(cents=250)) == domain.Price(domain.PriceSpec(cents=750))

    def test_an_order_is_for_at_least_one_unit(self) -> None:
        with pytest.raises(errors.DomainError):
            domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=0))

    def test_an_order_is_for_at_most_a_million_units(self) -> None:
        domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=1_000_000))
        with pytest.raises(errors.DomainError) as excinfo:
            domain.Order(domain.OrderSpec(order_id="o1", sku="widget", quantity=1_000_001))
        assert excinfo.value.code == "quantity_above_maximum"
