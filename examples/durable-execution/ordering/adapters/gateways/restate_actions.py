from __future__ import annotations

import tesser.adapters as ts
import restate
import restate.context

import ordering.application.ports.order_actions as order_actions
import tesser.errors as errors


class RestateOrderActions(ts.Gateway):

    def __init__(
        self,
        ctx: restate.Context,
        quote: restate.context.HandlerType[order_actions.QuoteRequest, order_actions.QuoteResponse],
    ) -> None:
        self._ctx = ctx
        self._quote = quote

    async def quote(self, request: order_actions.QuoteRequest) -> order_actions.QuoteResponse:
        try:
            return await self._ctx.service_call(self._quote, request)
        except restate.TerminalError as e:
            raise errors.DomainError(errors.Kind.NOT_FOUND, "action_rejected", e.message) from e
