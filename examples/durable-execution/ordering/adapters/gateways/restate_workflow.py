from __future__ import annotations

import json

import tesser.adapters as ts
import httpx
import restate
import restate.client
import restate.context
import restate.serde

import ordering.application.ports.order_workflow as order_workflow
import tesser.errors as errors


class RunRequest:  # tesser:debt TB052

    def __init__(self, sku: str, quantity: int) -> None:
        self.sku = sku
        self.quantity = quantity

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__


class RunResponse:  # tesser:debt TB052

    def __init__(self, order_id: str, total_cents: int) -> None:
        self.order_id = order_id
        self.total_cents = total_cents

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__


class RecordSerde[T](restate.serde.Serde[T]):  # tesser:debt TB052

    def __init__(self, kind: type[T]) -> None:
        self._kind = kind

    def serialize(self, obj: T | None) -> bytes:
        if obj is None:
            return b""
        return json.dumps(vars(obj)).encode()

    def deserialize(self, buf: bytes) -> T | None:
        if not buf:
            return None
        return self._kind(**json.loads(buf))


class RestateOrderWorkflow(ts.Gateway):

    def __init__(
        self,
        ingress: str,
        run: restate.context.HandlerType[RunRequest, RunResponse],
    ) -> None:
        self._ingress = ingress
        self._run = run

    async def start(self, request: order_workflow.StartRequest) -> order_workflow.StartResponse:
        try:
            async with httpx.AsyncClient(base_url=self._ingress) as http:
                await restate.client.Client(http).workflow_send(
                    self._run,
                    key=request.order_id,
                    arg=RunRequest(sku=request.sku, quantity=request.quantity),
                )
        except (restate.HttpError, httpx.TransportError) as e:
            raise errors.InfraError(f"restate ingress refused the workflow: {e}") from e
        return order_workflow.StartResponse(order_id=request.order_id)
