from __future__ import annotations

import tesser.testing as ts

import ordering.adapters.gateways as gateways
import ordering.application.ports as ports


@ts.helper
def charge_payment_method_request(
    order_id: str = "o1", cents: int = 750, payment_method: str = "card-4242"
) -> ports.ChargePaymentMethodRequest:
    return ports.ChargePaymentMethodRequest(
        order_id=order_id, cents=cents, payment_method=payment_method
    )


class TestMemoryPaymentProcessor:

    def test_a_charge_answers_a_receipt_naming_the_order_and_the_amount_asked(self) -> None:
        charge_payment_method_response = gateways.MemoryPaymentProcessor().charge_payment_method(
            charge_payment_method_request()
        )
        assert (
            charge_payment_method_response.outcome is ports.ChargePaymentMethodOutcome.CHARGED
        )
        assert charge_payment_method_response.order_id == "o1"
        assert charge_payment_method_response.receipts[0].reference == "pay-o1"
        assert charge_payment_method_response.receipts[0].cents == 750

    def test_an_identical_repeat_answers_the_original_receipt(self) -> None:
        memory_payment_processor = gateways.MemoryPaymentProcessor()
        first = memory_payment_processor.charge_payment_method(charge_payment_method_request())
        again = memory_payment_processor.charge_payment_method(charge_payment_method_request())
        assert again == first

    def test_a_repeat_for_another_amount_answers_the_original_receipt_unchanged(self) -> None:
        memory_payment_processor = gateways.MemoryPaymentProcessor()
        first = memory_payment_processor.charge_payment_method(charge_payment_method_request())
        again = memory_payment_processor.charge_payment_method(
            charge_payment_method_request(cents=700)
        )
        assert again == first
        assert again.receipts[0].cents == 750

    def test_a_payment_method_the_processor_refuses_is_declined(self) -> None:
        charge_payment_method_response = gateways.MemoryPaymentProcessor().charge_payment_method(
            charge_payment_method_request(payment_method="declined")
        )
        assert (
            charge_payment_method_response.outcome is ports.ChargePaymentMethodOutcome.DECLINED
        )
        assert charge_payment_method_response.receipts == ()
        assert "declined the charge" in charge_payment_method_response.reasons[0]

    def test_a_closed_processor_forgets_what_it_charged(self) -> None:
        memory_payment_processor = gateways.MemoryPaymentProcessor()
        memory_payment_processor.charge_payment_method(charge_payment_method_request())
        memory_payment_processor.close()
        charge_payment_method_response = memory_payment_processor.charge_payment_method(
            charge_payment_method_request(cents=700)
        )
        assert charge_payment_method_response.receipts[0].cents == 700
