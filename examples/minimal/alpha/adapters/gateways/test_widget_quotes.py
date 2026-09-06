from __future__ import annotations

import collections.abc as abc
import typing

import tesser.testing as ts

import alpha.adapters.gateways as gateways
import alpha.application.ports as ports


@ts.fake
class FakeJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O:
        return await step(None, request)


class TestWidgetQuoteGateway:

    def test_a_quote_answers_the_name_it_was_asked_for(self) -> None:
        quote_response = gateways.WidgetQuoteGateway().quote(
            FakeJobContext(), ports.QuoteRequest(name="a")
        )
        assert quote_response.name == "a"
