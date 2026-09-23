from __future__ import annotations

import json
import typing
import urllib.parse as urllib_parse

import tesser.adapters as ts
import httpx
import restate
import restate.client as restate_client

import ordering.application.relays as relays

_READ_TIMEOUT_SECONDS: typing.Final[float] = 30.0
_RUN_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=_READ_TIMEOUT_SECONDS)
_ALREADY_INVOKED: typing.Final[str] = "the workflow method was already invoked"


class RestateIngressOrderOrchestratorRelay(ts.Runner):

    def __init__(self, ingress: str) -> None:
        self._ingress = ingress

    async def start_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.StartConfirmOrderResponse:
        key = str(confirm_order_request.order.identity)
        async with httpx.AsyncClient(base_url=self._ingress) as async_client:
            await restate_client.Client(async_client).generic_send(
                "OrderOrchestrator",
                "confirm_order",
                relays.ConfirmOrderRequestSnapshot().serialize(confirm_order_request),
                key=urllib_parse.quote(key, safe=""),
                headers={"content-type": "application/json"},
            )
        return relays.StartConfirmOrderResponse(
            outcome=relays.StartConfirmOrderOutcome.STARTED, order_id=key
        )

    async def run_confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse:
        key = str(confirm_order_request.order.identity)
        try:
            async with httpx.AsyncClient(
                base_url=self._ingress, timeout=_RUN_TIMEOUT
            ) as async_client:
                return relays.ConfirmOrderResponseSnapshot().deserialize(
                    await restate_client.Client(async_client).generic_call(
                        "OrderOrchestrator",
                        "confirm_order",
                        relays.ConfirmOrderRequestSnapshot().serialize(confirm_order_request),
                        key=urllib_parse.quote(key, safe=""),
                        headers={"content-type": "application/json"},
                    )
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
            return relays.ConfirmOrderResponse(
                outcome=relays.ConfirmOrderOutcome.ALREADY_STARTED,
                order_id=key,
                confirmed_orders=(),
                reasons=(),
            )
