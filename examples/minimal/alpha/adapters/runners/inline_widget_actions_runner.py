from __future__ import annotations

import tesser.adapters as ts

import alpha.adapters.runtimes as runtimes
import alpha.application.relays as relays


class InlineWidgetActionsRunner(ts.Runner):

    def __init__(self, inline_widget_runtime: runtimes.InlineWidgetRuntime) -> None:
        self._inline_widget_runtime = inline_widget_runtime

    def run_quote_widget(self, quote_widget_request: relays.QuoteWidgetRequest) -> relays.QuoteWidgetResponse:
        return self._inline_widget_runtime.quote_handler(quote_widget_request)
