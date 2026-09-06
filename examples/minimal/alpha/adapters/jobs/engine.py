from __future__ import annotations

import collections.abc as abc
import typing

import tesser.adapters as ts

import alpha.application.client as client
import alpha.application.orchestrators as orchestrators
import alpha.application.ports as ports


class InlineJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O:
        return await step(None, request)


class EngineJob(ts.Job):

    def __init__(self, alpha_application_client: client.AlphaApplicationClient, quoting: ports.Quoting) -> None:
        self._alpha_application_client = alpha_application_client
        self._quoting = quoting

    def quote(self, quote_request: ports.QuoteRequest) -> ports.QuoteResponse:
        return self._alpha_application_client.quote(quote_request)

    def flow(self, quote_request: ports.QuoteRequest) -> orchestrators.FlowResponse:
        return orchestrators.WidgetFlow(InlineJobContext(), self._quoting).run(quote_request)
