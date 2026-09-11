from __future__ import annotations

import ordering.adapters.gateways as gateways
import ordering.application.ports as ports


class TestMemoryPaymentProcessor:

    def test_a_charge_answers_a_receipt_naming_the_order_and_the_amount_asked(self) -> None:
        charge_response = gateways.MemoryPaymentProcessor().charge(
            ports.ChargeRequest(order_id="o1", cents=750)
        )
        assert charge_response.order_id == "o1"
        assert charge_response.reference == "pay-o1"
        assert charge_response.cents == 750

    def test_an_identical_repeat_answers_the_original_receipt(self) -> None:
        memory_payment_processor = gateways.MemoryPaymentProcessor()
        first = memory_payment_processor.charge(ports.ChargeRequest(order_id="o1", cents=750))
        again = memory_payment_processor.charge(ports.ChargeRequest(order_id="o1", cents=750))
        assert again == first

    def test_a_repeat_for_another_amount_answers_the_original_receipt_unchanged(self) -> None:
        memory_payment_processor = gateways.MemoryPaymentProcessor()
        first = memory_payment_processor.charge(ports.ChargeRequest(order_id="o1", cents=750))
        again = memory_payment_processor.charge(ports.ChargeRequest(order_id="o1", cents=700))
        assert again == first
        assert again.cents == 750

    def test_a_closed_processor_forgets_what_it_charged(self) -> None:
        memory_payment_processor = gateways.MemoryPaymentProcessor()
        memory_payment_processor.charge(ports.ChargeRequest(order_id="o1", cents=750))
        memory_payment_processor.close()
        charge_response = memory_payment_processor.charge(
            ports.ChargeRequest(order_id="o1", cents=700)
        )
        assert charge_response.cents == 700
