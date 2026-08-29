from __future__ import annotations

import asyncio
import typing

import restate

import ordering.application.ports.order_actions as order_actions
import ordering.component.component as component
import ordering.component.config as config


class TestOrderingContext:

    def test_the_quote_job_quotes_through_the_wired_actions(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))

        async def call() -> order_actions.QuoteResponse:
            return await wired.jobs.quote(
                typing.cast(restate.Context, None), order_actions.QuoteRequest(sku="gadget")
            )

        try:
            quoted = asyncio.run(call())
        finally:
            wired.close()
        assert quoted.cents == 1000
