from __future__ import annotations

import typing

import tesser.application as ts


class QuoteRequest(ts.Request):

    sku: str

    def __init__(self, sku: str) -> None:
        self.sku = sku


class QuoteResponse(ts.Response):

    cents: int

    def __init__(self, cents: int) -> None:
        self.cents = cents


class Quoting(ts.Relay, typing.Protocol):

    async def quote(self, job: ts.JobContext, request: QuoteRequest) -> QuoteResponse: ...
