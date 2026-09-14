from __future__ import annotations

import tesser.adapters as ts

import alpha.adapters.runners as runners
import alpha.application.client as client
import alpha.application.orchestrators as orchestrators
import alpha.application.relays as relays


class InlineWidgetRuntime(ts.Runtime):

    def __init__(self, alpha_application_client: client.AlphaApplicationClient) -> None:
        self._alpha_application_client = alpha_application_client

    def keep_widget_handler(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        return self._alpha_application_client.keep_widget(keep_widget_request)

    def register_widget_handler(
        self, register_widget_request: relays.RegisterWidgetRequest
    ) -> relays.RegisterWidgetResponse:
        return orchestrators.WidgetOrchestrator(runners.InlineKeepWidgetRelay(self)).register_widget(
            register_widget_request
        )
