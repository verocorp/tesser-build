from __future__ import annotations

import tesser.adapters as ts

import alpha.adapters.runtimes as runtimes
import alpha.application.relays as relays


class InlineRegisterWidgetRelay(ts.Runner):

    def __init__(self, inline_widget_runtime: runtimes.InlineWidgetRuntime) -> None:
        self._inline_widget_runtime = inline_widget_runtime

    def run_register_widget(self, register_widget_request: relays.RegisterWidgetRequest) -> relays.RegisterWidgetResponse:
        return self._inline_widget_runtime.register_widget_handler(register_widget_request)
