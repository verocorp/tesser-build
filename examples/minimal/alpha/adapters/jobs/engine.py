from __future__ import annotations

import tesser.adapters as ts

import alpha.adapters.jobs.inline_context as inline_context
import alpha.application.client.widget_actions as widget_actions_client
import alpha.application.orchestrators.widget_flow as widget_flow
import alpha.application.ports.quoting as quoting


class EngineJob(ts.Job):

    def __init__(self, actions: widget_actions_client.Client, quotes: quoting.Quoting) -> None:
        self._actions = actions
        self._quotes = quotes

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        return self._actions.quote(request)

    def flow(self, request: quoting.QuoteRequest) -> widget_flow.FlowResponse:
        return widget_flow.WidgetFlow(inline_context.InlineJobContext(), self._quotes).run(request)
