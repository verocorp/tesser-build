from __future__ import annotations

import json

import tesser.adapters as ts

import ordering.client.client as client
import protocol.durable as durable


class WorkflowHandler(ts.Handler):

    def __init__(self, orchestrator: client.Orchestrator) -> None:
        self._orchestrator = orchestrator

    async def run(self, request: durable.WorkflowRequest) -> durable.WorkflowResponse:
        ran = await self._orchestrator.run(
            client.RunRequest(
                order_id=request.key, sku=request.text("sku"), quantity=request.integer("quantity")
            )
        )
        body = json.dumps({"order_id": ran.order_id, "total_cents": ran.total_cents}).encode()
        return durable.WorkflowResponse(body=body)
