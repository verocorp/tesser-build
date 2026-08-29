from __future__ import annotations

import pytest

import ordering.domain.order as order
import tesser.errors as errors


class TestOrder:

    def test_an_order_constructs_from_its_spec(self) -> None:
        spec = order.OrderSpec(order_id="o1", sku="widget", quantity=2)
        built = order.Order(spec)
        assert str(built.identity) == spec.order_id
        assert str(built.sku) == spec.sku
        assert int(built.quantity) == spec.quantity

    def test_the_total_is_the_unit_price_times_the_quantity(self) -> None:
        built = order.Order(order.OrderSpec(order_id="o1", sku="widget", quantity=3))
        assert built.total(order.PriceSpec(cents=250)) == order.Price(order.PriceSpec(cents=750))

    def test_an_order_is_for_at_least_one_unit(self) -> None:
        with pytest.raises(errors.DomainError):
            order.Order(order.OrderSpec(order_id="o1", sku="widget", quantity=0))


class TestPrice:

    def test_a_price_equals_by_value(self) -> None:
        assert order.Price(order.PriceSpec(cents=5)) == order.Price(order.PriceSpec(cents=5))

    def test_a_price_is_never_negative(self) -> None:
        with pytest.raises(errors.DomainError):
            order.Price(order.PriceSpec(cents=-1))
