from __future__ import annotations

import collections.abc as abc
import contextvars
import json
import typing

import tesser.adapters as ts

import ordering.application.ports.quotes as quotes
import tesser.errors as errors

ACTIONS: typing.Final[str] = "OrderingActions"
QUOTE: typing.Final[str] = "quote"


class RestateQuotes(ts.Gateway):

    def __init__(self) -> None:
        self._call: contextvars.ContextVar[abc.Callable[[str, str, bytes], abc.Awaitable[bytes]]] = (
            contextvars.ContextVar("durable_call")
        )

    def bind(self, call: abc.Callable[[str, str, bytes], abc.Awaitable[bytes]]) -> None:
        self._call.set(call)

    async def quote(self, request: quotes.QuoteRequest) -> quotes.QuoteResponse:
        try:
            call = self._call.get()
        except LookupError as e:
            raise errors.InfraError("no durable context is bound to this invocation") from e
        raw = await call(ACTIONS, QUOTE, json.dumps({"sku": request.sku}).encode())
        data = json.loads(raw)
        cents = data.get("cents") if isinstance(data, dict) else None
        if isinstance(cents, bool) or not isinstance(cents, int):
            raise errors.InfraError("the quote action answered without an integer cents")
        return quotes.QuoteResponse(cents=cents)
