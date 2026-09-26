from __future__ import annotations

import pytest

import ordering.domain as domain
import tesser.errors as errors


class TestOrderConfirmation:
    def test_a_confirmation_names_its_order(self) -> None:
        order_confirmation = domain.OrderConfirmation(
            domain.OrderConfirmationSpec(order_id="o1", quantity=3)
        )
        assert order_confirmation.identity == domain.OrderId("o1")

    def test_confirmation_records_the_total_computed_from_the_quote(self) -> None:
        order_confirmation = domain.OrderConfirmation(
            domain.OrderConfirmationSpec(order_id="o1", quantity=3)
        )
        assert (
            order_confirmation.confirm(
                domain.PriceQuoteSpec(outcome="priced", prices=(domain.PriceSpec(cents=250),))
            )
            is domain.OrderConfirmationOutcome.CONFIRMED
        )
        assert order_confirmation.total == domain.Price(domain.PriceSpec(cents=750))

    def test_an_unpriced_order_has_no_confirmed_total(self) -> None:
        order_confirmation = domain.OrderConfirmation(
            domain.OrderConfirmationSpec(order_id="o1", quantity=3)
        )
        assert (
            order_confirmation.confirm(domain.PriceQuoteSpec(outcome="price_not_found", prices=()))
            is domain.OrderConfirmationOutcome.PRICE_NOT_FOUND
        )
        with pytest.raises(errors.DomainError) as excinfo:
            _ = order_confirmation.total
        assert excinfo.value.code == "order_not_confirmed"

    def test_a_confirmed_order_cannot_be_repriced(self) -> None:
        order_confirmation = domain.OrderConfirmation(
            domain.OrderConfirmationSpec(order_id="o1", quantity=3)
        )
        order_confirmation.confirm(
            domain.PriceQuoteSpec(outcome="priced", prices=(domain.PriceSpec(cents=250),))
        )
        with pytest.raises(errors.DomainError) as excinfo:
            order_confirmation.confirm(
                domain.PriceQuoteSpec(outcome="priced", prices=(domain.PriceSpec(cents=100),))
            )
        assert excinfo.value.code == "order_already_confirmed"
        assert order_confirmation.total == domain.Price(domain.PriceSpec(cents=750))

    def test_a_quote_cannot_contradict_its_prices(self) -> None:
        order_confirmation = domain.OrderConfirmation(
            domain.OrderConfirmationSpec(order_id="o1", quantity=3)
        )
        for price_quote_spec in (
            domain.PriceQuoteSpec(outcome="priced", prices=()),
            domain.PriceQuoteSpec(outcome="price_not_found", prices=(domain.PriceSpec(cents=250),)),
            domain.PriceQuoteSpec(
                outcome="priced", prices=(domain.PriceSpec(cents=250), domain.PriceSpec(cents=300))
            ),
            domain.PriceQuoteSpec(outcome="unknown", prices=()),
        ):
            with pytest.raises(errors.DomainError) as excinfo:
                order_confirmation.confirm(price_quote_spec)
            assert excinfo.value.code == "invalid_quote"
        assert (
            order_confirmation.confirm(
                domain.PriceQuoteSpec(outcome="priced", prices=(domain.PriceSpec(cents=250),))
            )
            is domain.OrderConfirmationOutcome.CONFIRMED
        )

    def test_a_failed_total_does_not_confirm_the_order(self) -> None:
        order_confirmation = domain.OrderConfirmation(
            domain.OrderConfirmationSpec(order_id="o1", quantity=3)
        )
        with pytest.raises(errors.DomainError):
            order_confirmation.confirm(
                domain.PriceQuoteSpec(outcome="priced", prices=(domain.PriceSpec(cents=10**12),))
            )
        with pytest.raises(errors.DomainError) as excinfo:
            _ = order_confirmation.total
        assert excinfo.value.code == "order_not_confirmed"

    def test_confirmation_validates_the_order_and_quantity_it_will_price(self) -> None:
        for order_confirmation_spec in (
            domain.OrderConfirmationSpec(order_id="", quantity=1),
            domain.OrderConfirmationSpec(order_id="o1", quantity=0),
            domain.OrderConfirmationSpec(order_id="o1", quantity=1_000_001),
        ):
            with pytest.raises(errors.DomainError):
                domain.OrderConfirmation(order_confirmation_spec)
