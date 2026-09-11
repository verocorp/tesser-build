from __future__ import annotations

import typing

import tesser.application as ts


class QuoteRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class QuoteResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class WidgetActionsRunner(ts.Relay, typing.Protocol):

    def run_quote(self, quote_request: QuoteRequest) -> QuoteResponse: ...
