from __future__ import annotations

import tesser.adapters as ts
import httpx
import restate
import restate.client
import restate.context

import ordering.application.ports as ports
import tesser.errors as errors


class RestateOrderWorkflow(ts.Gateway):

    def __init__(
        self,
        ingress: str,
        run: restate.context.HandlerType[ports.StartRequest, object],
    ) -> None:
        self._ingress = ingress
        self._run = run

    async def start(self, start_request: ports.StartRequest) -> ports.StartResponse:
        try:
            async with httpx.AsyncClient(base_url=self._ingress) as http:
                await restate.client.Client(http).workflow_send(
                    self._run, key=start_request.order_id, arg=start_request
                )
        except (restate.HttpError, httpx.TransportError) as e:
            raise errors.InfraError(f"restate ingress refused the workflow: {e}") from e
        return ports.StartResponse(order_id=start_request.order_id)
