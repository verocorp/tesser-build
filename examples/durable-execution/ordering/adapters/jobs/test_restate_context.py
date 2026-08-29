from __future__ import annotations

import asyncio
import typing

import restate

import ordering.adapters.jobs.restate_context as restate_context
import ordering.application.ports.quoting as quoting


class TestRestateJobContext:

    def test_call_journals_the_step_through_the_invocations_context(self) -> None:
        seen: list[str] = []

        class Journaling:
            async def service_call(
                self,
                tpe: restate.context.HandlerType[quoting.QuoteRequest, quoting.QuoteResponse],
                arg: quoting.QuoteRequest,
            ) -> quoting.QuoteResponse:
                seen.append(arg.sku)
                return quoting.QuoteResponse(cents=250)

        async def quote(ctx: restate.Context, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
            return quoting.QuoteResponse(cents=0)

        job = restate_context.RestateJobContext(typing.cast(restate.Context, Journaling()))
        quoted = asyncio.run(job.call(quote, quoting.QuoteRequest(sku="widget")))
        assert quoted.cents == 250
        assert seen == ["widget"]
