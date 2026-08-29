from __future__ import annotations

import tesser.adapters as ts
import restate
import restate.context

import ordering.application.ports.quoting as quoting
import tesser.errors as errors


class RestateQuoting(ts.Gateway):

    def __init__(
        self,
        ctx: restate.Context,
        quote: restate.context.HandlerType[quoting.QuoteRequest, quoting.QuoteResponse],
    ) -> None:
        self._ctx = ctx
        self._quote = quote

    async def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        try:
            return await self._ctx.service_call(self._quote, request)
        except restate.TerminalError as e:
            raise errors.DomainError(errors.Kind.NOT_FOUND, "action_rejected", e.message) from e
