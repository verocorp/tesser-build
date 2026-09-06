from __future__ import annotations

import json  # tesser:debt TB062
import typing

import tesser.application as ts


class PrepareQuoteRequest(ts.Request):  # tesser:debt TB052

    def __init__(self, sku: str) -> None:
        self.sku = sku


class PrepareQuoteRequestSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, prepare_quote_request: PrepareQuoteRequest) -> bytes:
        return json.dumps({"sku": prepare_quote_request.sku}).encode()

    def deserialize(self, buf: bytes) -> PrepareQuoteRequest:
        return PrepareQuoteRequest(sku=json.loads(buf)["sku"])


class PrepareQuoteResponse(ts.Response):  # tesser:debt TB052

    def __init__(self, cents: int) -> None:
        self.cents = cents


class PrepareQuoteResponseSnapshot(ts.Serde):  # tesser:debt TB052

    def serialize(self, prepare_quote_response: PrepareQuoteResponse) -> bytes:
        return json.dumps({"cents": prepare_quote_response.cents}).encode()

    def deserialize(self, buf: bytes) -> PrepareQuoteResponse:
        return PrepareQuoteResponse(cents=json.loads(buf)["cents"])


class OrderActionsRunner(ts.JobContext, typing.Protocol):  # tesser:debt TB052

    async def run_prepare_quote(
        self, prepare_quote_request: PrepareQuoteRequest
    ) -> PrepareQuoteResponse: ...
