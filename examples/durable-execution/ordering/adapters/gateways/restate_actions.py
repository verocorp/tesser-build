from __future__ import annotations

import json

import tesser.adapters as ts
import restate
import restate.extensions

import ordering.application.ports.order_actions as order_actions
import tesser.errors as errors


class RestateOrderActions(ts.Gateway):

    def __init__(self, service: str, handler: str) -> None:
        self._service = service
        self._handler = handler

    async def quote(self, request: order_actions.QuoteRequest) -> order_actions.QuoteResponse:
        try:
            ctx = restate.extensions.current_context()
        except LookupError as e:
            raise errors.InfraError("quote was called outside a restate invocation") from e
        if ctx is None:
            raise errors.InfraError("quote was called outside a restate invocation")
        body = json.dumps({"sku": request.sku}).encode()
        try:
            raw = await ctx.generic_call(
                self._service, self._handler, body, headers={"content-type": "application/json"}
            )
        except restate.TerminalError as e:
            raise errors.DomainError(errors.Kind.NOT_FOUND, "action_rejected", e.message) from e
        data = json.loads(raw)
        cents = data.get("cents") if isinstance(data, dict) else None
        if isinstance(cents, bool) or not isinstance(cents, int):
            raise errors.InfraError("the quote action answered without an integer cents")
        return order_actions.QuoteResponse(cents=cents)
