from __future__ import annotations

import asyncio
import typing

import restate

import ordering.component.component as component
import ordering.component.config as config
import protocol.durable as durable


class TestOrderingContext:

    def test_the_quote_handler_quotes_through_the_wired_actions(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))

        async def call() -> durable.QuoteResponse:
            return await wired.handlers.quote(
                typing.cast(restate.Context, None), durable.QuoteRequest(sku="gadget")
            )

        try:
            quoted = asyncio.run(call())
        finally:
            wired.close()
        assert quoted == durable.QuoteResponse(cents=1000)
