from __future__ import annotations

import tesser.adapters as ts

import alpha.adapters.jobs.inline_context as inline_context
import alpha.application.client as client
import alpha.application.orchestrators as orchestrators
import alpha.application.ports as ports


class EngineJob(ts.Job):

    def __init__(self, application_client: client.Client, quoting: ports.Quoting) -> None:
        self._application_client = application_client
        self._quoting = quoting

    def quote(self, quote_request: ports.QuoteRequest) -> ports.QuoteResponse:
        return self._application_client.quote(quote_request)

    def flow(self, quote_request: ports.QuoteRequest) -> orchestrators.FlowResponse:
        return orchestrators.WidgetFlow(inline_context.InlineJobContext(), self._quoting).run(quote_request)
