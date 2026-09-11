from __future__ import annotations

import tesser.application as ts

import alpha.application.relays as relays
import alpha.domain as domain


class FlowResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class MapToQuoteRequest(ts.Mapper, relays.QuoteRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name))


class MapToFlowResponse(ts.Mapper, FlowResponse):

    def __init__(self, quote_response: relays.QuoteResponse) -> None:
        super().__init__(name=quote_response.name)


class WidgetFlow(ts.Orchestrator):

    def __init__(self, widget_actions_runner: relays.WidgetActionsRunner) -> None:
        self._widget_actions_runner = widget_actions_runner

    def run(self, quote_request: relays.QuoteRequest) -> FlowResponse:
        name = domain.Name(quote_request.name)
        quote_response = self._widget_actions_runner.run_quote(MapToQuoteRequest(name))
        return MapToFlowResponse(quote_response)
