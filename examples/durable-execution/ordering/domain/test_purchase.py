from __future__ import annotations

import pytest

import ordering.domain as domain
import tesser.errors as errors


class TestPayment:
    def test_a_payment_constructs_from_its_spec(self) -> None:
        payment = domain.Payment(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750))
        assert str(payment.reference) == "pay-o1"
        assert payment.amount == domain.Price(domain.PriceSpec(cents=750))

    def test_a_payment_equals_by_value(self) -> None:
        assert domain.Payment(
            domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750)
        ) == domain.Payment(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750))
        assert domain.Payment(
            domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750)
        ) != domain.Payment(domain.PaymentSpec(order_id="o1", reference="pay-o2", cents=750))

    def test_a_payment_reference_is_never_empty(self) -> None:
        with pytest.raises(errors.DomainError):
            domain.Payment(domain.PaymentSpec(order_id="o1", reference="", cents=750))

    def test_a_payment_names_the_order_it_settles(self) -> None:
        payment = domain.Payment(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750))
        assert payment.order_id == domain.OrderId("o1")


class TestPaymentMethod:
    def test_a_payment_method_constructs_from_its_value(self) -> None:
        assert str(domain.PaymentMethod("card-4242")) == "card-4242"

    def test_a_payment_method_equals_by_value(self) -> None:
        assert domain.PaymentMethod("card-4242") == domain.PaymentMethod("card-4242")
        assert domain.PaymentMethod("card-4242") != domain.PaymentMethod("card-1234")

    def test_a_payment_method_is_never_empty(self) -> None:
        with pytest.raises(errors.DomainError):
            domain.PaymentMethod("")


class TestPurchase:
    def test_a_confirmation_cannot_supply_two_totals(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        with pytest.raises(errors.DomainError) as excinfo:
            purchase.confirm(
                domain.PurchaseConfirmationSpec(
                    order_id="o1", totals=(domain.PriceSpec(cents=750), domain.PriceSpec(cents=800))
                )
            )
        assert excinfo.value.code == "invalid_confirmation"
        with pytest.raises(errors.DomainError) as excinfo:
            _ = purchase.total
        assert excinfo.value.code == "purchase_not_confirmed"

    def test_a_purchase_constructs_from_its_spec(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        assert purchase.identity == domain.OrderId("o1")
        assert (
            purchase.confirm(
                domain.PurchaseConfirmationSpec(
                    order_id="o1", totals=(domain.PriceSpec(cents=750),)
                )
            )
            is domain.PurchaseConfirmationOutcome.CONFIRMED
        )
        assert purchase.total == domain.Price(domain.PriceSpec(cents=750))

    def test_a_payment_of_the_total_settles_the_purchase(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        purchase.confirm(
            domain.PurchaseConfirmationSpec(order_id="o1", totals=(domain.PriceSpec(cents=750),))
        )
        assert (
            purchase.settle(
                domain.PaymentResultSpec(
                    outcome="taken",
                    payments=(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750),),
                )
            )
            is domain.PurchaseSettlementOutcome.PAID
        )
        assert purchase.payment == domain.Payment(
            domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750)
        )

    def test_a_payment_of_another_amount_is_a_conflict(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        purchase.confirm(
            domain.PurchaseConfirmationSpec(order_id="o1", totals=(domain.PriceSpec(cents=750),))
        )
        with pytest.raises(errors.DomainError) as excinfo:
            purchase.settle(
                domain.PaymentResultSpec(
                    outcome="taken",
                    payments=(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=700),),
                )
            )
        assert excinfo.value.kind is errors.Kind.CONFLICT
        assert excinfo.value.code == "payment_mismatch"

    def test_a_purchase_is_never_for_a_negative_total(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        with pytest.raises(errors.DomainError):
            purchase.confirm(
                domain.PurchaseConfirmationSpec(order_id="o1", totals=(domain.PriceSpec(cents=-1),))
            )

    def test_a_pricing_of_another_order_cannot_be_purchased(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        with pytest.raises(errors.DomainError) as excinfo:
            purchase.confirm(
                domain.PurchaseConfirmationSpec(
                    order_id="o2", totals=(domain.PriceSpec(cents=750),)
                )
            )
        assert excinfo.value.kind is errors.Kind.CONFLICT
        assert excinfo.value.code == "priced_another_order"

    def test_a_payment_for_another_order_does_not_settle_the_purchase(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        purchase.confirm(
            domain.PurchaseConfirmationSpec(order_id="o1", totals=(domain.PriceSpec(cents=750),))
        )
        with pytest.raises(errors.DomainError) as excinfo:
            purchase.settle(
                domain.PaymentResultSpec(
                    outcome="taken",
                    payments=(domain.PaymentSpec(order_id="o2", reference="pay-o2", cents=750),),
                )
            )
        assert excinfo.value.kind is errors.Kind.CONFLICT
        assert excinfo.value.code == "payment_for_another_order"

    def test_an_unconfirmed_purchase_cannot_be_paid(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        with pytest.raises(errors.DomainError) as excinfo:
            purchase.settle(
                domain.PaymentResultSpec(
                    outcome="taken",
                    payments=(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750),),
                )
            )
        assert excinfo.value.code == "purchase_not_confirmed"
        with pytest.raises(errors.DomainError) as excinfo:
            _ = purchase.total
        assert excinfo.value.code == "purchase_not_confirmed"

    def test_an_unavailable_confirmation_records_no_payable_total(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        assert (
            purchase.confirm(domain.PurchaseConfirmationSpec(order_id="o1", totals=()))
            is domain.PurchaseConfirmationOutcome.ORDER_NOT_CONFIRMED
        )
        with pytest.raises(errors.DomainError) as excinfo:
            _ = purchase.total
        assert excinfo.value.code == "purchase_not_confirmed"

    def test_confirmation_cannot_replace_an_agreed_total(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        purchase.confirm(
            domain.PurchaseConfirmationSpec(order_id="o1", totals=(domain.PriceSpec(cents=750),))
        )
        with pytest.raises(errors.DomainError) as excinfo:
            purchase.confirm(
                domain.PurchaseConfirmationSpec(
                    order_id="o1", totals=(domain.PriceSpec(cents=900),)
                )
            )
        assert excinfo.value.code == "purchase_already_confirmed"
        assert purchase.total == domain.Price(domain.PriceSpec(cents=750))

    def test_a_declined_payment_does_not_settle_the_purchase(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        purchase.confirm(
            domain.PurchaseConfirmationSpec(order_id="o1", totals=(domain.PriceSpec(cents=750),))
        )
        assert (
            purchase.settle(domain.PaymentResultSpec(outcome="declined", payments=()))
            is domain.PurchaseSettlementOutcome.DECLINED
        )
        with pytest.raises(errors.DomainError) as excinfo:
            _ = purchase.payment
        assert excinfo.value.code == "purchase_not_paid"

    def test_a_payment_result_cannot_contradict_its_receipts(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        purchase.confirm(
            domain.PurchaseConfirmationSpec(order_id="o1", totals=(domain.PriceSpec(cents=750),))
        )
        for payment_result_spec in (
            domain.PaymentResultSpec(outcome="taken", payments=()),
            domain.PaymentResultSpec(
                outcome="declined",
                payments=(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750),),
            ),
            domain.PaymentResultSpec(
                outcome="taken",
                payments=(
                    domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750),
                    domain.PaymentSpec(order_id="o1", reference="pay-o2", cents=750),
                ),
            ),
            domain.PaymentResultSpec(outcome="unknown", payments=()),
        ):
            with pytest.raises(errors.DomainError) as excinfo:
                purchase.settle(payment_result_spec)
            assert excinfo.value.code == "invalid_payment_result"

    def test_a_failed_receipt_does_not_settle_the_purchase(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        purchase.confirm(
            domain.PurchaseConfirmationSpec(order_id="o1", totals=(domain.PriceSpec(cents=750),))
        )
        with pytest.raises(errors.DomainError):
            purchase.settle(
                domain.PaymentResultSpec(
                    outcome="taken",
                    payments=(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=700),),
                )
            )
        with pytest.raises(errors.DomainError) as excinfo:
            _ = purchase.payment
        assert excinfo.value.code == "purchase_not_paid"
        assert (
            purchase.settle(
                domain.PaymentResultSpec(
                    outcome="taken",
                    payments=(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750),),
                )
            )
            is domain.PurchaseSettlementOutcome.PAID
        )

    def test_a_settled_purchase_cannot_be_paid_again(self) -> None:
        purchase = domain.Purchase(domain.PurchaseSpec(order_id="o1"))
        purchase.confirm(
            domain.PurchaseConfirmationSpec(order_id="o1", totals=(domain.PriceSpec(cents=750),))
        )
        purchase.settle(
            domain.PaymentResultSpec(
                outcome="taken",
                payments=(domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750),),
            )
        )
        with pytest.raises(errors.DomainError) as excinfo:
            purchase.settle(
                domain.PaymentResultSpec(
                    outcome="taken",
                    payments=(domain.PaymentSpec(order_id="o1", reference="pay-o2", cents=750),),
                )
            )
        assert excinfo.value.code == "purchase_already_paid"
        assert purchase.payment == domain.Payment(
            domain.PaymentSpec(order_id="o1", reference="pay-o1", cents=750)
        )
