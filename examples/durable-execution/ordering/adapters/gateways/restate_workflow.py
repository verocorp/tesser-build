from __future__ import annotations

import tesser.adapters as ts
import httpx
import restate
import restate.context

import ordering.application.ports.order_workflow as order_workflow
import protocol.durable as durable
import tesser.errors as errors


class RestateOrderWorkflow(ts.Gateway):

    def __init__(
        self,
        client: restate.RestateClient,
        run: restate.context.HandlerType[durable.RunRequest, durable.RunResponse],
    ) -> None:
        self._client = client
        self._run = run

    async def start(self, request: order_workflow.StartRequest) -> order_workflow.StartResponse:
        try:
            await self._client.workflow_send(
                self._run,
                key=request.order_id,
                arg=durable.RunRequest(sku=request.sku, quantity=request.quantity),
            )
        except (restate.HttpError, httpx.TransportError) as e:
            raise errors.InfraError(f"restate ingress refused the workflow: {e}") from e
        return order_workflow.StartResponse(order_id=request.order_id)
