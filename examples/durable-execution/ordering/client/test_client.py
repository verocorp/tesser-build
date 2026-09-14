from __future__ import annotations

import ordering.client as client


class TestOrderRejected:

    def test_a_rejected_order_carries_its_code_and_message(self) -> None:
        order_rejected = client.OrderRejected(
            "quantity_below_one", "an order is for at least one unit"
        )
        assert order_rejected.code == "quantity_below_one"
        assert order_rejected.message == "an order is for at least one unit"
        assert str(order_rejected) == "an order is for at least one unit"


class TestProductPriceNotFound:

    def test_a_price_that_was_not_found_carries_its_message(self) -> None:
        product_price_not_found = client.ProductPriceNotFound("no price for sku 'nope'")
        assert product_price_not_found.message == "no price for sku 'nope'"
        assert str(product_price_not_found) == "no price for sku 'nope'"


class TestOrderNotConfirmed:

    def test_an_order_that_was_not_confirmed_carries_its_message(self) -> None:
        order_not_confirmed = client.OrderNotConfirmed("no price for sku 'nope'")
        assert order_not_confirmed.message == "no price for sku 'nope'"
        assert str(order_not_confirmed) == "no price for sku 'nope'"


class TestPaymentDeclined:

    def test_a_declined_payment_carries_its_message(self) -> None:
        payment_declined = client.PaymentDeclined("the processor declined the charge")
        assert payment_declined.message == "the processor declined the charge"
        assert str(payment_declined) == "the processor declined the charge"


class TestOrderAlreadyStarted:

    def test_an_order_already_started_carries_its_message(self) -> None:
        order_already_started = client.OrderAlreadyStarted(
            "the workflow method was already invoked"
        )
        assert order_already_started.message == "the workflow method was already invoked"
        assert str(order_already_started) == "the workflow method was already invoked"


class TestErrors:

    def test_the_declared_set_names_every_error_the_client_raises(self) -> None:
        raised = {
            name
            for name, value in vars(client).items()
            if isinstance(value, type) and issubclass(value, Exception)
        }
        assert {error.__name__ for error in client.ERRORS} == raised
