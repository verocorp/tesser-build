from __future__ import annotations

import json
import typing

import tesser.application as ts


class QuoteRequest(ts.Request):

    def __init__(self, sku: str) -> None:
        self.sku = sku


class QuoteRequestSnapshot(ts.Serde):

    def serialize(self, request: QuoteRequest) -> bytes:
        return json.dumps({"sku": request.sku}).encode()

    def deserialize(self, buf: bytes) -> QuoteRequest:
        return QuoteRequest(sku=json.loads(buf)["sku"])


class QuoteResponse(ts.Response):

    def __init__(self, cents: int) -> None:
        self.cents = cents


class QuoteResponseSnapshot(ts.Serde):

    def serialize(self, response: QuoteResponse) -> bytes:
        return json.dumps({"cents": response.cents}).encode()

    def deserialize(self, buf: bytes) -> QuoteResponse:
        return QuoteResponse(cents=json.loads(buf)["cents"])


class OrderJobContext(ts.JobContext, typing.Protocol):

    async def quote(self, request: QuoteRequest) -> QuoteResponse: ...
