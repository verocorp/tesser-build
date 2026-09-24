from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.relays as relays


class WidgetOrchestratorApplicationClient(ts.Client, typing.Protocol):

    def register_widget(self, register_widget_request: relays.RegisterWidgetRequest) -> relays.RegisterWidgetResponse: ...
