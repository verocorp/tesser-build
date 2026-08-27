from __future__ import annotations

import json
import typing

import tesser.adapters as ts
import httpx
import restate

import ordering.application.ports.order_workflow as order_workflow
import tesser.errors as errors

WORKFLOW: typing.Final[str] = "Ordering"
RUN: typing.Final[str] = "run"


class RestateOrderWorkflow(ts.Gateway):

    def __init__(self, client: restate.RestateClient) -> None:
        self._client = client

    async def start(self, request: order_workflow.StartRequest) -> order_workflow.StartResponse:
        body = json.dumps({"sku": request.sku, "quantity": request.quantity}).encode()
        try:
            await self._client.generic_send(
                WORKFLOW, RUN, body, key=request.order_id, headers={"content-type": "application/json"}
            )
        except (restate.HttpError, httpx.TransportError) as e:
            raise errors.InfraError(f"restate ingress refused the workflow: {e}") from e
        return order_workflow.StartResponse(order_id=request.order_id)
