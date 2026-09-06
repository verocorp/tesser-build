from __future__ import annotations  # tesser:debt TB041

import urllib.parse

import tesser.adapters as ts
import httpx
import restate
import restate.client

import ordering.adapters.runtimes as runtimes
import ordering.application.relays as relays  # tesser:debt TB060
import tesser.errors as errors


class RestateOrderOrchestratorRunner(ts.Gateway):

    def __init__(self, ingress: str, restate_order_runtime: runtimes.RestateOrderRuntime) -> None:
        self._ingress = ingress
        self._restate_order_runtime = restate_order_runtime

    async def start_order_orchestrator(
        self, order_orchestrator_request: relays.OrderOrchestratorRequest
    ) -> relays.StartOrderOrchestratorResponse:
        key = str(order_orchestrator_request.order.identity)
        try:
            async with httpx.AsyncClient(base_url=self._ingress) as async_client:
                await restate.client.Client(async_client).workflow_send(
                    self._restate_order_runtime.order_orchestrator_handler,
                    key=urllib.parse.quote(key, safe=""),
                    arg=order_orchestrator_request,
                )
        except (restate.HttpError, httpx.TransportError) as transport_error:
            raise errors.InfraError(
                f"restate ingress refused the workflow: {transport_error}"
            ) from transport_error
        return relays.StartOrderOrchestratorResponse(key)
