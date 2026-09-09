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
        self.charged: list[tuple[str, int]] = []

    def charge(self, charge_request: ports.ChargeRequest) -> ports.ChargeResponse:
        self.charged.append((charge_request.order_id, charge_request.cents))
        return ports.ChargeResponse(
            order_id=charge_request.order_id,
            reference=f"pay-{charge_request.order_id}",
            cents=charge_request.cents,
        )


@ts.fake
class FakeRefusingPaymentProcessor(ports.PaymentProcessor):

    def charge(self, charge_request: ports.ChargeRequest) -> ports.ChargeResponse:
        raise errors.conflict(
            "payment_already_taken", f"order {charge_request.order_id!r} has already been charged"
        )


class TestPurchaseActions:

    def test_taking_a_payment_answers_the_processors_reference_and_amount(self) -> None:
        take_payment_response = application.PurchaseActions(FakePaymentProcessor()).take_payment(
            relays.TakePaymentRequest(order_id="o1", cents=750)
        )
        assert take_payment_response.order_id == "o1"
        assert take_payment_response.reference == "pay-o1"
        assert take_payment_response.cents == 750

    def test_taking_a_payment_charges_the_order_once_for_the_amount(self) -> None:
        fake_payment_processor = FakePaymentProcessor()
        application.PurchaseActions(fake_payment_processor).take_payment(
            relays.TakePaymentRequest(order_id="o2", cents=3000)
        )
        assert fake_payment_processor.charged == [("o2", 3000)]

    def test_a_refused_charge_is_the_processors_conflict(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            application.PurchaseActions(FakeRefusingPaymentProcessor()).take_payment(
                relays.TakePaymentRequest(order_id="o1", cents=750)
            )
        assert excinfo.value.kind is errors.Kind.CONFLICT

    def test_a_negative_amount_is_refused_before_the_processor_is_asked(self) -> None:
        fake_payment_processor = FakePaymentProcessor()
        with pytest.raises(errors.DomainError):
            application.PurchaseActions(fake_payment_processor).take_payment(
                relays.TakePaymentRequest(order_id="o1", cents=-1)
            )
        assert fake_payment_processor.charged == []
