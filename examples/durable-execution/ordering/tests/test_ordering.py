from __future__ import annotations

import asyncio
import typing

import restate

import ordering.application.ports.quoting as quoting
import ordering.component.component as component
import ordering.component.config as config


class TestOrderingContext:

    def test_the_quote_job_quotes_through_the_wired_actions(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))

        async def call() -> quoting.QuoteResponse:
            return await wired.jobs.quote(
                typing.cast(restate.Context, None), quoting.QuoteRequest(sku="gadget")
            )

        try:
            quoted = asyncio.run(call())
        finally:
            wired.close()
        assert quoted.cents == 1000
