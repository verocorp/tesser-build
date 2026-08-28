from __future__ import annotations

import json

import tesser.adapters as ts
import httpx
import restate

import ordering.application.ports.order_workflow as order_workflow
import tesser.errors as errors


class RestateOrderWorkflow(ts.Gateway):

    def __init__(self, client: restate.RestateClient, service: str, handler: str) -> None:
        self._client = client
        self._service = service
        self._handler = handler

    async def start(self, request: order_workflow.StartRequest) -> order_workflow.StartResponse:
        body = json.dumps({"sku": request.sku, "quantity": request.quantity}).encode()
        try:
            await self._client.generic_send(
                self._service,
                self._handler,
                body,
                key=request.order_id,
                headers={"content-type": "application/json"},
            )
        except (restate.HttpError, httpx.TransportError) as e:
            raise errors.InfraError(f"restate ingress refused the workflow: {e}") from e
        return order_workflow.StartResponse(order_id=request.order_id)
