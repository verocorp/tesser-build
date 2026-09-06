from __future__ import annotations

import asyncio
import collections.abc as abc
import typing

import tesser.testing as ts
import pytest
import restate

import ordering.adapters.gateways as gateways
import ordering.application.ports as ports
import tesser.errors as errors


@ts.fake
class FakeJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I  # tesser:debt TB022
    ) -> O:
        return await step(None, request)


class TestRestateQuoting:

    def test_the_quoted_cents_come_back_as_the_ports_response(self) -> None:
        service = restate.Service("OrderingActions")

        @service.handler()
        async def quote(ctx: restate.Context, request: ports.QuoteRequest) -> ports.QuoteResponse:  # tesser:debt TB023
            return ports.QuoteResponse(cents=250)

        restate_quoting = gateways.RestateQuoting(quote)
        quote_response = asyncio.run(
            restate_quoting.quote(FakeJobContext(), ports.QuoteRequest(sku="widget"))
        )
        assert quote_response.cents == 250

    def test_a_terminal_error_from_the_action_becomes_a_domain_error(self) -> None:
        service = restate.Service("OrderingActions")

        @service.handler()
        async def quote(ctx: restate.Context, request: ports.QuoteRequest) -> ports.QuoteResponse:  # tesser:debt TB023
            raise restate.TerminalError("no price for sku 'nope'", status_code=404)

        restate_quoting = gateways.RestateQuoting(quote)
        with pytest.raises(errors.DomainError):
            asyncio.run(restate_quoting.quote(FakeJobContext(), ports.QuoteRequest(sku="nope")))
