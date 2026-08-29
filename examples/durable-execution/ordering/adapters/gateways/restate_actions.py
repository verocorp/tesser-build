from __future__ import annotations

import tesser.adapters as ts
import restate
import restate.context

import ordering.application.ports.order_actions as order_actions
import tesser.errors as errors


class QuoteRequest:  # tesser:debt TB052

    def __init__(self, sku: str) -> None:
        self.sku = sku

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__


class QuoteResponse:  # tesser:debt TB052

    def __init__(self, cents: int) -> None:
        self.cents = cents

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__


class RestateOrderActions(ts.Gateway):

    def __init__(
        self,
        ctx: restate.Context,
        quote: restate.context.HandlerType[QuoteRequest, QuoteResponse],
    ) -> None:
        self._ctx = ctx
        self._quote = quote

    async def quote(self, request: order_actions.QuoteRequest) -> order_actions.QuoteResponse:
        try:
            quoted = await self._ctx.service_call(self._quote, QuoteRequest(sku=request.sku))
        except restate.TerminalError as e:
            raise errors.DomainError(errors.Kind.NOT_FOUND, "action_rejected", e.message) from e
        return order_actions.QuoteResponse(cents=quoted.cents)
