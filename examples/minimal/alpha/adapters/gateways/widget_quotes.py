from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports as ports


class WidgetQuoteGateway(ts.Gateway):

    def quote(self, job_context: ts.JobContext, quote_request: ports.QuoteRequest) -> ports.QuoteResponse:
        return ports.QuoteResponse(name=quote_request.name)
