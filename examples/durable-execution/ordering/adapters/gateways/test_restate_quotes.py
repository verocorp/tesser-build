from __future__ import annotations

import asyncio
import json

import pytest

import ordering.adapters.gateways.restate_quotes as restate_quotes
import ordering.application.ports.quotes as quotes
import tesser.errors as errors


class TestRestateQuotes:

    def test_a_quote_calls_the_action_and_reads_the_cents(self) -> None:
        called: list[tuple[str, str, bytes]] = []

        async def call(service: str, handler: str, arg: bytes) -> bytes:
            called.append((service, handler, arg))
            return b'{"cents": 250}'

        gateway = restate_quotes.RestateQuotes()

        async def quote() -> quotes.QuoteResponse:
            gateway.bind(call)
            return await gateway.quote(quotes.QuoteRequest(sku="widget"))

        quoted = asyncio.run(quote())

        assert quoted.cents == 250
        service, handler, arg = called[0]
        assert (service, handler) == (restate_quotes.ACTIONS, restate_quotes.QUOTE)
        assert json.loads(arg) == {"sku": "widget"}

    def test_an_unbound_invocation_is_an_infra_error(self) -> None:
        gateway = restate_quotes.RestateQuotes()
        with pytest.raises(errors.InfraError):
            asyncio.run(gateway.quote(quotes.QuoteRequest(sku="widget")))

    def test_an_answer_without_cents_is_an_infra_error(self) -> None:
        async def call(service: str, handler: str, arg: bytes) -> bytes:
            return b'{"cents": "250"}'

        gateway = restate_quotes.RestateQuotes()

        async def quote() -> quotes.QuoteResponse:
            gateway.bind(call)
            return await gateway.quote(quotes.QuoteRequest(sku="widget"))

        with pytest.raises(errors.InfraError):
            asyncio.run(quote())
