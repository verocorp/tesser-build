from __future__ import annotations

import pytest

import ordering.adapters.gateways as gateways
import ordering.application.ports as ports
import tesser.errors as errors


class TestMemoryPaymentProcessor:

    def test_a_charge_answers_a_reference_for_the_amount_asked(self) -> None:
        charge_response = gateways.MemoryPaymentProcessor().charge(
            ports.ChargeRequest(order_id="o1", cents=750)
        )
        assert charge_response.reference == "pay-o1"
        assert charge_response.cents == 750

    def test_an_order_is_charged_once(self) -> None:
        memory_payment_processor = gateways.MemoryPaymentProcessor()
        memory_payment_processor.charge(ports.ChargeRequest(order_id="o1", cents=750))
        with pytest.raises(errors.DomainError) as excinfo:
            memory_payment_processor.charge(ports.ChargeRequest(order_id="o1", cents=750))
        assert excinfo.value.kind is errors.Kind.CONFLICT
        assert excinfo.value.code == "payment_already_taken"

    def test_a_closed_processor_forgets_what_it_charged(self) -> None:
        memory_payment_processor = gateways.MemoryPaymentProcessor()
        memory_payment_processor.charge(ports.ChargeRequest(order_id="o1", cents=750))
        memory_payment_processor.close()
        charge_response = memory_payment_processor.charge(
            ports.ChargeRequest(order_id="o1", cents=750)
        )
        assert charge_response.reference == "pay-o1"
