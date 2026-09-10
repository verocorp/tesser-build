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


class TestOrderId:

    def test_an_order_id_is_never_a_dot_segment(self) -> None:
        for value in (".", ".."):
            with pytest.raises(errors.DomainError) as excinfo:
                domain.OrderId(value)
            assert excinfo.value.code == "dotted_order_id"
        assert str(domain.OrderId("..x")) == "..x"


class TestPrice:

    def test_a_price_equals_by_value(self) -> None:
        assert domain.Price(domain.PriceSpec(cents=5)) == domain.Price(domain.PriceSpec(cents=5))

    def test_a_price_is_never_negative(self) -> None:
        with pytest.raises(errors.DomainError):
            domain.Price(domain.PriceSpec(cents=-1))

    def test_a_price_is_at_most_a_trillion_cents(self) -> None:
        domain.Price(domain.PriceSpec(cents=10**12))
        with pytest.raises(errors.DomainError) as excinfo:
            domain.Price(domain.PriceSpec(cents=10**12 + 1))
        assert excinfo.value.code == "price_above_maximum"


class TestPayment:

    def test_a_payment_constructs_from_its_spec(self) -> None:
        payment = domain.Payment(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750))
        assert str(payment.reference) == "pay-o1"
        assert payment.amount == domain.Price(domain.PriceSpec(cents=750))

    def test_a_payment_equals_by_value(self) -> None:
        assert domain.Payment(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750)) == domain.Payment(
            domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750)
        )
        assert domain.Payment(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750)) != domain.Payment(
            domain.PaymentSpec(order_id="o1", reference="pay-o2", cents=750)
        )

    def test_a_payment_reference_is_never_empty(self) -> None:
        with pytest.raises(errors.DomainError):
            domain.Payment(domain.PaymentSpec(order_id="o1", reference="", cents=750))

    def test_a_payment_names_the_order_it_settles(self) -> None:
        payment = domain.Payment(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750))
        assert payment.order_id == domain.OrderId("o1")


class TestPurchase:

    def test_a_purchase_constructs_from_its_spec(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1", priced_order_id="o1", total_cents=750))
        assert purchase.identity == domain.OrderId("o1")
        assert purchase.total == domain.Price(domain.PriceSpec(cents=750))

    def test_a_payment_of_the_total_settles_the_purchase(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1", priced_order_id="o1", total_cents=750))
        payment = purchase.paid(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750))
        assert payment == domain.Payment(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750))

    def test_a_payment_of_another_amount_is_a_conflict(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1", priced_order_id="o1", total_cents=750))
        with pytest.raises(errors.DomainError) as excinfo:
            purchase.paid(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=700))
        assert excinfo.value.kind is errors.Kind.CONFLICT
        assert excinfo.value.code == "payment_mismatch"

    def test_a_purchase_is_never_for_a_negative_total(self) -> None:
        with pytest.raises(errors.DomainError):
            domain.Purchase(domain.PurchaseSpec(order_id="o1", priced_order_id="o1", total_cents=-1))

    def test_a_pricing_of_another_order_cannot_be_purchased(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            domain.Purchase(domain.PurchaseSpec(order_id="o1", priced_order_id="o2", total_cents=750))
        assert excinfo.value.kind is errors.Kind.CONFLICT
        assert excinfo.value.code == "priced_another_order"

    def test_a_payment_for_another_order_does_not_settle_the_purchase(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1", priced_order_id="o1", total_cents=750))
        with pytest.raises(errors.DomainError) as excinfo:
            purchase.paid(domain.PaymentSpec(order_id="o2", reference="pay-o2", cents=750))
        assert excinfo.value.kind is errors.Kind.CONFLICT
        assert excinfo.value.code == "payment_for_another_order"
