from __future__ import annotations

import tesser.testing as ts
import pytest

import ordering.application as application
import ordering.application.ports as ports
import ordering.application.relays as relays
import tesser.errors as errors


@ts.fake
class FakePaymentProcessor(ports.PaymentProcessor):

    def __init__(self) -> None:
        self.charged: list[tuple[str, int, str]] = []

    def charge_payment_method(
        self, charge_payment_method_request: ports.ChargePaymentMethodRequest
    ) -> ports.ChargePaymentMethodResponse:
        self.charged.append(
            (
                charge_payment_method_request.order_id,
                charge_payment_method_request.cents,
                charge_payment_method_request.payment_method,
            )
        )
        return ports.ChargePaymentMethodResponse(
            outcome=ports.ChargePaymentMethodOutcome.CHARGED,
            order_id=charge_payment_method_request.order_id,
            receipts=(
                ports.Receipt(
                    reference=f"pay-{charge_payment_method_request.order_id}",
                    cents=charge_payment_method_request.cents,
                ),
            ),
            reasons=(),
        )


@ts.fake
class FakeDecliningPaymentProcessor(ports.PaymentProcessor):

    def charge_payment_method(
        self, charge_payment_method_request: ports.ChargePaymentMethodRequest
    ) -> ports.ChargePaymentMethodResponse:
        return ports.ChargePaymentMethodResponse(
            outcome=ports.ChargePaymentMethodOutcome.DECLINED,
            order_id=charge_payment_method_request.order_id,
            receipts=(),
            reasons=(
                f"the processor declined the charge for order "
                f"{charge_payment_method_request.order_id!r}",
            ),
        )


@ts.helper
def take_payment_request(
    order_id: str = "o1", cents: int = 750, payment_method: str = "card-4242"
) -> relays.TakePaymentRequest:
    return relays.TakePaymentRequest(
        order_id=order_id, cents=cents, payment_method=payment_method
    )


class TestPurchaseActions:

    def test_taking_a_payment_answers_the_processors_reference_and_amount(self) -> None:
        take_payment_response = application.PurchaseActions(FakePaymentProcessor()).take_payment(
            take_payment_request()
        )
        assert take_payment_response.outcome is relays.TakePaymentOutcome.TAKEN
        assert take_payment_response.order_id == "o1"
        assert take_payment_response.payments[0].reference == "pay-o1"
        assert take_payment_response.payments[0].cents == 750

    def test_taking_a_payment_charges_the_named_method_once_for_the_amount(self) -> None:
        fake_payment_processor = FakePaymentProcessor()
        application.PurchaseActions(fake_payment_processor).take_payment(
            take_payment_request(order_id="o2", cents=3000, payment_method="card-1234")
        )
        assert fake_payment_processor.charged == [("o2", 3000, "card-1234")]

    def test_a_declined_charge_carries_the_processors_word_forward(self) -> None:
        take_payment_response = application.PurchaseActions(
            FakeDecliningPaymentProcessor()
        ).take_payment(take_payment_request())
        assert take_payment_response.outcome is relays.TakePaymentOutcome.DECLINED
        assert take_payment_response.payments == ()
        assert "declined the charge" in take_payment_response.reasons[0]

    def test_an_empty_payment_method_is_a_fault_and_the_processor_is_never_asked(self) -> None:
        fake_payment_processor = FakePaymentProcessor()
        with pytest.raises(errors.DomainError):
            application.PurchaseActions(fake_payment_processor).take_payment(
                take_payment_request(payment_method="")
            )
        assert fake_payment_processor.charged == []

    def test_a_negative_amount_is_a_fault_and_the_processor_is_never_asked(self) -> None:
        fake_payment_processor = FakePaymentProcessor()
        with pytest.raises(errors.DomainError):
            application.PurchaseActions(fake_payment_processor).take_payment(
                take_payment_request(cents=-1)
            )
        assert fake_payment_processor.charged == []
