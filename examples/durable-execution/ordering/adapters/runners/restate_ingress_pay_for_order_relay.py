from __future__ import annotations

import json
import typing
import urllib.parse as urllib_parse

import tesser.adapters as ts
import httpx
import restate
import restate.client as restate_client

import ordering.adapters.runtimes as runtimes
import ordering.application.relays as relays

_READ_TIMEOUT_SECONDS: typing.Final[float] = 30.0
_RUN_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=_READ_TIMEOUT_SECONDS)
_ALREADY_INVOKED: typing.Final[str] = "the workflow method was already invoked"


class RestateIngressPayForOrderRelay(ts.Runner):

    def __init__(self, ingress: str, restate_order_runtime: runtimes.RestateOrderRuntime) -> None:
        self._ingress = ingress
        self._restate_order_runtime = restate_order_runtime

    async def run_pay_for_order(
        self, pay_for_order_request: relays.PayForOrderRequest
    ) -> relays.PayForOrderResponse:
        key = str(pay_for_order_request.order.identity)
        try:
            async with httpx.AsyncClient(
                base_url=self._ingress, timeout=_RUN_TIMEOUT
            ) as async_client:
                return await restate_client.Client(async_client).workflow_call(
                    self._restate_order_runtime.pay_for_order_handler,
                    key=urllib_parse.quote(key, safe=""),
                    arg=pay_for_order_request,
                )
        except restate.HttpError as http_error:
            if http_error.status_code != 409:
                raise
            try:
                refusal = json.loads(http_error.body or "")
            except (ValueError, RecursionError):
                refusal = None
            if not (
                isinstance(refusal, dict)
                and refusal.get("code") == 409
                and refusal.get("message") == _ALREADY_INVOKED
            ):
                raise
            return relays.PayForOrderResponse(
                outcome=relays.PayForOrderOutcome.ALREADY_STARTED,
                order_id=key,
                purchases=(),
                reasons=(),
            )
