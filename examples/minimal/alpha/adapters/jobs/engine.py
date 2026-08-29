from __future__ import annotations

import tesser.adapters as ts

import alpha.application.client.widget_actions as widget_actions_client
import alpha.application.orchestrators.widget_flow as widget_flow
import alpha.application.ports.widget_actions as widget_actions


class EngineJob(ts.Job):

    def __init__(
        self, actions: widget_actions_client.Client, quotes: widget_actions.WidgetActions
    ) -> None:
        self._actions = actions
        self._quotes = quotes

    def quote(self, request: widget_actions.QuoteRequest) -> widget_actions.QuoteResponse:
        return self._actions.quote(request)

    def flow(self, request: widget_actions.QuoteRequest) -> widget_flow.FlowResponse:
        return widget_flow.WidgetFlow(self._quotes).run(request)
