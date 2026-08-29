from __future__ import annotations

import asyncio
import collections.abc as abc
import typing

import tesser.testing as ts
import pytest
import restate

import ordering.adapters.gateways.restate_quoting as restate_quoting
import ordering.application.ports.quoting as quoting
import tesser.errors as errors


@ts.fake
class FakeJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O:
        return await step(None, request)


class TestRestateQuoting:

    def test_the_quoted_cents_come_back_as_the_ports_response(self) -> None:
        service = restate.Service("OrderingActions")

        @service.handler()
        async def quote(ctx: restate.Context, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
            return quoting.QuoteResponse(cents=250)

        gateway = restate_quoting.RestateQuoting(quote)
        quoted = asyncio.run(gateway.quote(FakeJobContext(), quoting.QuoteRequest(sku="widget")))
        assert quoted.cents == 250

    def test_a_terminal_error_from_the_action_becomes_a_domain_error(self) -> None:
        service = restate.Service("OrderingActions")

        @service.handler()
        async def quote(ctx: restate.Context, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
            raise restate.TerminalError("no price for sku 'nope'", status_code=404)

        gateway = restate_quoting.RestateQuoting(quote)
        with pytest.raises(errors.DomainError):
            asyncio.run(gateway.quote(FakeJobContext(), quoting.QuoteRequest(sku="nope")))
