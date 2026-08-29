from __future__ import annotations

import tesser.application as ts

import alpha.application.ports.widget_actions as widget_actions
import alpha.domain.widget as widget


class FlowResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class MapToQuoteRequest(ts.Mapper, widget_actions.QuoteRequest):

    def __init__(self, named: widget.Name) -> None:
        super().__init__(name=str(named))


class MapToFlowResponse(ts.Mapper, FlowResponse):

    def __init__(self, quoted: widget_actions.QuoteResponse) -> None:
        super().__init__(name=quoted.name)


class WidgetFlow(ts.Orchestrator):

    def __init__(self, quotes: widget_actions.WidgetActions) -> None:
        self._quotes = quotes

    def run(self, request: widget_actions.QuoteRequest) -> FlowResponse:
        named = widget.Name(request.name)
        quoted = self._quotes.quote(MapToQuoteRequest(named))
        return MapToFlowResponse(quoted)
