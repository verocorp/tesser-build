from __future__ import annotations

import collections.abc as abc
import typing

import tesser.testing as ts

import alpha.adapters.gateways.widget_quotes as widget_quotes
import alpha.application.ports.quoting as quoting


@ts.fake
class FakeJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O:
        return await step(None, request)


class TestWidgetQuoteGateway:

    def test_a_quote_answers_the_name_it_was_asked_for(self) -> None:
        quoted = widget_quotes.WidgetQuoteGateway().quote(
            FakeJobContext(), quoting.QuoteRequest(name="a")
        )
        assert quoted.name == "a"
