from __future__ import annotations

import tesser.adapters as ts

import alpha.adapters.runners as runners
import alpha.application.client as client
import alpha.application.orchestrators as orchestrators
import alpha.application.relays as relays


class InlineWidgetRuntime(ts.Runtime):

    def __init__(self, alpha_application_client: client.AlphaApplicationClient) -> None:
        self._alpha_application_client = alpha_application_client

    def quote_handler(self, quote_widget_request: relays.QuoteWidgetRequest) -> relays.QuoteWidgetResponse:
        return self._alpha_application_client.quote_widget(quote_widget_request)

    def widget_flow_handler(self, quote_widget_request: relays.QuoteWidgetRequest) -> orchestrators.FlowResponse:
        return orchestrators.WidgetFlow(runners.InlineWidgetActionsRunner(self)).quote_widget(quote_widget_request)
