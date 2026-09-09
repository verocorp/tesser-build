from __future__ import annotations

import ordering.application.relays as relays


class TestTakePaymentRequestSnapshot:

    def test_a_request_is_the_order_id_and_the_amount(self) -> None:
        raw = relays.TakePaymentRequestSnapshot().serialize(
            relays.TakePaymentRequest(order_id="o1", cents=750)
        )
        assert raw == b'{"order_id": "o1", "cents": 750}'

    def test_a_request_comes_back_equal(self) -> None:
        take_payment_request_snapshot = relays.TakePaymentRequestSnapshot()  # tesser:debt TB085
        take_payment_request = relays.TakePaymentRequest(order_id="o1", cents=750)
        assert take_payment_request_snapshot.deserialize(
            take_payment_request_snapshot.serialize(take_payment_request)
        ) == take_payment_request


class TestTakePaymentResponseSnapshot:

    def test_a_response_is_the_reference_and_the_amount_charged(self) -> None:
        raw = relays.TakePaymentResponseSnapshot().serialize(
            relays.TakePaymentResponse(reference="pay-o1", cents=750)
        )
        assert raw == b'{"reference": "pay-o1", "cents": 750}'

    def test_a_response_comes_back_equal(self) -> None:
        take_payment_response_snapshot = relays.TakePaymentResponseSnapshot()  # tesser:debt TB085
        take_payment_response = relays.TakePaymentResponse(reference="pay-o1", cents=750)
        assert take_payment_response_snapshot.deserialize(
            take_payment_response_snapshot.serialize(take_payment_response)
        ) == take_payment_response
