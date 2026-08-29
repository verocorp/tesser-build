from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.quoting as quoting


class WidgetQuoteGateway(ts.Gateway):

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        return quoting.QuoteResponse(name=request.name)
