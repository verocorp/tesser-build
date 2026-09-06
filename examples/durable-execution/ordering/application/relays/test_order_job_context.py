from __future__ import annotations

import ordering.application.relays.order_job_context as order_job_context


class TestQuoteRequestSnapshot:

    def test_a_quote_request_is_its_sku(self) -> None:
        raw = order_job_context.QuoteRequestSnapshot().serialize(
            order_job_context.QuoteRequest(sku="widget")
        )
        assert raw == b'{"sku": "widget"}'

    def test_a_quote_request_comes_back_equal(self) -> None:
        snapshot = order_job_context.QuoteRequestSnapshot()
        asked = order_job_context.QuoteRequest(sku="gadget")
        assert snapshot.deserialize(snapshot.serialize(asked)) == asked


class TestQuoteResponseSnapshot:

    def test_a_quote_response_is_its_cents(self) -> None:
        raw = order_job_context.QuoteResponseSnapshot().serialize(
            order_job_context.QuoteResponse(cents=250)
        )
        assert raw == b'{"cents": 250}'

    def test_a_quote_response_comes_back_equal(self) -> None:
        snapshot = order_job_context.QuoteResponseSnapshot()
        answered = order_job_context.QuoteResponse(cents=250)
        assert snapshot.deserialize(snapshot.serialize(answered)) == answered
