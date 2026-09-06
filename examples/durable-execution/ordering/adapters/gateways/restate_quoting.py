from __future__ import annotations

import collections.abc as abc
import typing

import tesser.adapters as ts
import restate

import ordering.application.ports as ports
import tesser.errors as errors


class RestateQuoting(ts.Gateway):

    def __init__(
        self,
        quote: abc.Callable[[typing.Any, ports.QuoteRequest], abc.Awaitable[ports.QuoteResponse]],
    ) -> None:
        self._quote = quote

    async def quote(
        self, job_context: ts.JobContext, quote_request: ports.QuoteRequest
    ) -> ports.QuoteResponse:
        try:
            return await job_context.call(self._quote, quote_request)
        except restate.TerminalError as e:
            raise errors.DomainError(errors.Kind.NOT_FOUND, "action_rejected", e.message) from e
