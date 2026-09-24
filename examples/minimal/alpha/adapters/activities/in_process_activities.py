from __future__ import annotations

import tesser.adapters as ts
import in_process

import alpha.application.client as client
import alpha.application.relays as relays


class InProcessKeepWidget(ts.Activity):

    def __init__(
        self, widget_actions_service: in_process.Service, widget_application_client: client.WidgetApplicationClient
    ) -> None:
        @widget_actions_service.handler()
        def keep_widget(
            in_process_context: in_process.Context, keep_widget_request: relays.KeepWidgetRequest
        ) -> relays.KeepWidgetResponse:
            return widget_application_client.keep_widget(keep_widget_request)

        self.handler = keep_widget
