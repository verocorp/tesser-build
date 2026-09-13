from __future__ import annotations

import pytest

import ordering.application.relays as relays


class TestTakePaymentRequestSnapshot:

    def test_a_request_is_the_order_id_the_amount_and_the_payment_method(self) -> None:
        raw = relays.TakePaymentRequestSnapshot().serialize(
            relays.TakePaymentRequest(order_id="o1", cents=750, payment_method="card-4242")
        )
        assert raw == b'{"order_id": "o1", "cents": 750, "payment_method": "card-4242"}'

    def test_a_request_comes_back_equal(self) -> None:
        take_payment_request_snapshot = relays.TakePaymentRequestSnapshot()
        take_payment_request = relays.TakePaymentRequest(
            order_id="o1", cents=750, payment_method="card-4242"
        )
        assert take_payment_request_snapshot.deserialize(
            take_payment_request_snapshot.serialize(take_payment_request)
        ) == take_payment_request

    def test_a_request_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"order_id": "o1", "cents": 750}',
            b'{"order_id": "o1", "cents": -1, "payment_method": "card-4242"}',
            b'{"order_id": "o1", "cents": true, "payment_method": "card-4242"}',
            b'{"order_id": "o1", "cents": "750", "payment_method": "card-4242"}',
            b'{"order_id": 1, "cents": 750, "payment_method": "card-4242"}',
            b'{"order_id": "", "cents": 750, "payment_method": "card-4242"}',
            b'{"order_id": "o1", "cents": 750, "payment_method": ""}',
            b'{"order_id": "o1", "cents": 750, "payment_method": 7}',
            b'["o1", 750]',
        ):
            with pytest.raises(ValueError):
                relays.TakePaymentRequestSnapshot().deserialize(raw)


class TestTakePaymentResponseSnapshot:

    def test_a_taken_response_is_its_outcome_the_order_and_the_one_payment(self) -> None:
        raw = relays.TakePaymentResponseSnapshot().serialize(
            relays.TakePaymentResponse(
                outcome=relays.TakePaymentOutcome.TAKEN,
                order_id="o1",
                payments=(relays.Payment(reference="pay-o1", cents=750),),
                reasons=(),
            )
        )
        assert raw == (
            b'{"outcome": "taken", "order_id": "o1", '
            b'"payments": [{"reference": "pay-o1", "cents": 750}], "reasons": []}'
        )

    def test_a_declined_response_carries_no_payment_and_its_reason(self) -> None:
        raw = relays.TakePaymentResponseSnapshot().serialize(
            relays.TakePaymentResponse(
                outcome=relays.TakePaymentOutcome.DECLINED,
                order_id="o1",
                payments=(),
                reasons=("the processor declined the charge",),
            )
        )
        assert raw == (
            b'{"outcome": "declined", "order_id": "o1", "payments": [], '
            b'"reasons": ["the processor declined the charge"]}'
        )

    def test_a_response_comes_back_equal(self) -> None:
        take_payment_response_snapshot = relays.TakePaymentResponseSnapshot()
        take_payment_response = relays.TakePaymentResponse(
            outcome=relays.TakePaymentOutcome.TAKEN,
            order_id="o1",
            payments=(relays.Payment(reference="pay-o1", cents=750),),
            reasons=(),
        )
        assert take_payment_response_snapshot.deserialize(
            take_payment_response_snapshot.serialize(take_payment_response)
        ) == take_payment_response

    def test_a_response_of_the_wrong_shape_is_refused_before_the_constructor(self) -> None:
        for raw in (
            b'{"outcome": "taken", "order_id": "o1"}',
            b'{"outcome": "taken", "payments": [], "reasons": []}',
            b'{"outcome": "taken", "order_id": "", "payments": [], "reasons": []}',
            b'{"outcome": "taken", "order_id": 1, "payments": [], "reasons": []}',
            b'{"outcome": "taken", "order_id": "o1", "payments": [{"reference": "pay-o1", "cents": -1}], "reasons": []}',
            b'{"outcome": "taken", "order_id": "o1", "payments": [{"reference": "pay-o1", "cents": true}], "reasons": []}',
            b'{"outcome": "taken", "order_id": "o1", "payments": [{"reference": 7, "cents": 750}], "reasons": []}',
            b'{"outcome": "taken", "order_id": "o1", "payments": [{"reference": "", "cents": 750}], "reasons": []}',
            b'{"outcome": "taken", "order_id": "o1", "payments": [], "reasons": []}',
            b'{"outcome": "declined", "order_id": "o1", "payments": [{"reference": "pay-o1", "cents": 750}], "reasons": []}',
            b'{"outcome": "refused", "order_id": "o1", "payments": [], "reasons": []}',
            b'["o1", "pay-o1", 750]',
        ):
            with pytest.raises(ValueError):
                relays.TakePaymentResponseSnapshot().deserialize(raw)
