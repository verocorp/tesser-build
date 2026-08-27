from __future__ import annotations

import typing

import tesser.application as ts


class QuoteRequest(ts.Request):

    def __init__(self, sku: str) -> None:
        self.sku = sku


class QuoteResponse(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class Quotes(ts.Port, typing.Protocol):

    async def quote(self, request: QuoteRequest) -> QuoteResponse: ...
