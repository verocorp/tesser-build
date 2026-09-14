from __future__ import annotations

import tesser.application as ts

import alpha.application.relays as relays
import alpha.domain as domain


class FlowResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class MapToQuoteWidgetRequest(ts.Mapper, relays.QuoteWidgetRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name))


class MapToFlowResponse(ts.Mapper, FlowResponse):

    def __init__(self, quote_widget_response: relays.QuoteWidgetResponse) -> None:
        super().__init__(name=quote_widget_response.name)


class WidgetFlow(ts.Orchestrator):

    def __init__(self, widget_actions_runner: relays.WidgetActionsRunner) -> None:
        self._widget_actions_runner = widget_actions_runner

    def quote_widget(self, quote_widget_request: relays.QuoteWidgetRequest) -> FlowResponse:
        name = domain.Name(quote_widget_request.name)
        quote_widget_response = self._widget_actions_runner.run_quote_widget(MapToQuoteWidgetRequest(name))
        return MapToFlowResponse(quote_widget_response)
