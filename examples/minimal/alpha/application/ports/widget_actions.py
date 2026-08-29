from __future__ import annotations

import typing

import tesser.application as ts


class QuoteRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class QuoteResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class WidgetActions(ts.Port, typing.Protocol):

    def quote(self, request: QuoteRequest) -> QuoteResponse: ...
