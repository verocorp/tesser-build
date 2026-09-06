from __future__ import annotations

import ordering.application.relays as relays


class TestPrepareQuoteRequestSnapshot:

    def test_a_request_is_its_sku(self) -> None:
        raw = relays.PrepareQuoteRequestSnapshot().serialize(relays.PrepareQuoteRequest(sku="widget"))
        assert raw == b'{"sku": "widget"}'

    def test_a_request_comes_back_equal(self) -> None:
        prepare_quote_request_snapshot = relays.PrepareQuoteRequestSnapshot()  # tesser:debt TB085
        prepare_quote_request = relays.PrepareQuoteRequest(sku="gadget")
        assert prepare_quote_request_snapshot.deserialize(
            prepare_quote_request_snapshot.serialize(prepare_quote_request)
        ) == prepare_quote_request


class TestPrepareQuoteResponseSnapshot:

    def test_a_response_is_its_cents(self) -> None:
        raw = relays.PrepareQuoteResponseSnapshot().serialize(relays.PrepareQuoteResponse(cents=250))
        assert raw == b'{"cents": 250}'

    def test_a_response_comes_back_equal(self) -> None:
        prepare_quote_response_snapshot = relays.PrepareQuoteResponseSnapshot()  # tesser:debt TB085
        prepare_quote_response = relays.PrepareQuoteResponse(cents=250)
        assert prepare_quote_response_snapshot.deserialize(
            prepare_quote_response_snapshot.serialize(prepare_quote_response)
        ) == prepare_quote_response
