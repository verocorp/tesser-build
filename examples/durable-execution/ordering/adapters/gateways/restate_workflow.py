from __future__ import annotations

import asyncio
import collections.abc as abc
import json
import typing

import tesser.adapters as ts
import httpx
import restate

import ordering.application.ports.order_workflow as order_workflow
import tesser.errors as errors

WORKFLOW: typing.Final[str] = "Ordering"
RUN: typing.Final[str] = "run"


class RestateIngress(ts.Gateway):

    def __init__(self, ingress: str) -> None:
        self._ingress = ingress

    async def send(self, service: str, handler: str, arg: bytes, key: str) -> None:
        async with restate.create_client(self._ingress) as client:
            await client.generic_send(service, handler, arg, key=key, headers={"content-type": "application/json"})


class RestateOrderWorkflow(ts.Gateway):

    def __init__(self, send: abc.Callable[[str, str, bytes, str], abc.Coroutine[object, object, None]]) -> None:
        self._send = send

    def start(self, request: order_workflow.StartRequest) -> order_workflow.StartResponse:
        body = json.dumps({"sku": request.sku, "quantity": request.quantity}).encode()
        try:
            asyncio.run(self._send(WORKFLOW, RUN, body, request.order_id))
        except (restate.HttpError, httpx.TransportError) as e:
            raise errors.InfraError(f"restate ingress refused the workflow: {e}") from e
        return order_workflow.StartResponse(order_id=request.order_id)
