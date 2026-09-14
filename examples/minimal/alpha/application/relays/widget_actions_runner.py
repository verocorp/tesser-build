from __future__ import annotations

import typing

import tesser.application as ts


class QuoteWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class QuoteWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class WidgetActionsRunner(ts.Relay, typing.Protocol):

    def run_quote_widget(self, quote_widget_request: QuoteWidgetRequest) -> QuoteWidgetResponse: ...
