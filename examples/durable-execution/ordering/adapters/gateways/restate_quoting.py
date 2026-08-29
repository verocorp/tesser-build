from __future__ import annotations

import collections.abc as abc
import typing

import tesser.adapters as ts
import restate

import ordering.application.ports.quoting as quoting
import tesser.errors as errors


class RestateQuoting(ts.Gateway):

    def __init__(
        self,
        quote: abc.Callable[[typing.Any, quoting.QuoteRequest], abc.Awaitable[quoting.QuoteResponse]],
    ) -> None:
        self._quote = quote

    async def quote(self, job: ts.JobContext, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        try:
            return await job.call(self._quote, request)
        except restate.TerminalError as e:
            raise errors.DomainError(errors.Kind.NOT_FOUND, "action_rejected", e.message) from e
