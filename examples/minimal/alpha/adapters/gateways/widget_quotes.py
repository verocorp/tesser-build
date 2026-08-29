from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.widget_actions as widget_actions


class WidgetQuoteGateway(ts.Gateway):

    def quote(self, request: widget_actions.QuoteRequest) -> widget_actions.QuoteResponse:
        return widget_actions.QuoteResponse(name=request.name)
