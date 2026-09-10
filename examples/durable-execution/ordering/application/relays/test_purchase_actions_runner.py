from __future__ import annotations

import pytest

import ordering.application.relays as relays
import tesser.errors as errors


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

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"order_id": "o1"}',
            b'{"order_id": "o1", "cents": -1}',
            b'{"order_id": "o1", "cents": true}',
            b'{"order_id": "o1", "cents": "750"}',
            b'{"order_id": 1, "cents": 750}',
            b'{"order_id": "", "cents": 750}',
            b'["o1", 750]',
        ):
            with pytest.raises(errors.DomainError) as excinfo:
                relays.TakePaymentRequestSnapshot().deserialize(raw)
            assert excinfo.value.kind is errors.Kind.VALIDATION


class TestTakePaymentResponseSnapshot:

    def test_a_response_is_the_order_the_reference_and_the_amount_charged(self) -> None:
        raw = relays.TakePaymentResponseSnapshot().serialize(
            relays.TakePaymentResponse(order_id="o1", reference="pay-o1", cents=750)
        )
        assert raw == b'{"order_id": "o1", "reference": "pay-o1", "cents": 750}'

    def test_a_response_comes_back_equal(self) -> None:
        take_payment_response_snapshot = relays.TakePaymentResponseSnapshot()  # tesser:debt TB085
        take_payment_response = relays.TakePaymentResponse(order_id="o1", reference="pay-o1", cents=750)
        assert take_payment_response_snapshot.deserialize(
            take_payment_response_snapshot.serialize(take_payment_response)
        ) == take_payment_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"order_id": "o1", "reference": "pay-o1"}',
            b'{"reference": "pay-o1", "cents": 750}',
            b'{"order_id": "", "reference": "pay-o1", "cents": 750}',
            b'{"order_id": 1, "reference": "pay-o1", "cents": 750}',
            b'{"order_id": "o1", "reference": "pay-o1", "cents": -1}',
            b'{"order_id": "o1", "reference": "pay-o1", "cents": true}',
            b'{"order_id": "o1", "reference": "pay-o1", "cents": "750"}',
            b'{"order_id": "o1", "reference": 7, "cents": 750}',
            b'{"order_id": "o1", "reference": "", "cents": 750}',
            b'["o1", "pay-o1", 750]',
        ):
            with pytest.raises(errors.DomainError) as excinfo:
                relays.TakePaymentResponseSnapshot().deserialize(raw)
            assert excinfo.value.kind is errors.Kind.VALIDATION
