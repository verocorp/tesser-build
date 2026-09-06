from __future__ import annotations

import collections.abc as abc
import json
import typing

import tesser.adapters as ts
import httpx
import restate
import restate.client
import restate.context
import restate.serde

import ordering.application.client.order_actions as order_actions_client
import ordering.application.orchestrators.order_orchestrator as order_orchestrator
import ordering.application.relays.order_relay as order_relay
import tesser.errors as errors


class RestateStartRequestSerde(ts.Serde, restate.serde.Serde[order_relay.StartRequest]):

    def serialize(self, obj: order_relay.StartRequest | None) -> bytes:
        if obj is None:
            return b""
        return order_relay.OrderSnapshot().serialize(obj.order)

    def deserialize(self, buf: bytes) -> order_relay.StartRequest | None:
        if not buf:
            return None
        return order_relay.StartRequest(order=order_relay.OrderSnapshot().deserialize(buf))


class RestateQuoteRequestSerde(ts.Serde, restate.serde.Serde[order_relay.QuoteRequest]):

    def serialize(self, obj: order_relay.QuoteRequest | None) -> bytes:
        if obj is None:
            return b""
        return json.dumps({"sku": obj.sku}).encode()

    def deserialize(self, buf: bytes) -> order_relay.QuoteRequest | None:
        if not buf:
            return None
        return order_relay.QuoteRequest(sku=json.loads(buf)["sku"])


class RestateQuoteResponseSerde(ts.Serde, restate.serde.Serde[order_relay.QuoteResponse]):

    def serialize(self, obj: order_relay.QuoteResponse | None) -> bytes:
        if obj is None:
            return b""
        return json.dumps({"cents": obj.cents}).encode()

    def deserialize(self, buf: bytes) -> order_relay.QuoteResponse | None:
        if not buf:
            return None
        return order_relay.QuoteResponse(cents=json.loads(buf)["cents"])


class RestateRunResponseSerde(ts.Serde, restate.serde.Serde[order_orchestrator.RunResponse]):

    def serialize(self, obj: order_orchestrator.RunResponse | None) -> bytes:
        if obj is None:
            return b""
        return json.dumps({"order_id": obj.order_id, "total_cents": obj.total_cents}).encode()

    def deserialize(self, buf: bytes) -> order_orchestrator.RunResponse | None:
        if not buf:
            return None
        read = json.loads(buf)
        return order_orchestrator.RunResponse(
            order_id=read["order_id"], total_cents=read["total_cents"]
        )


class RestateOrderRelay(ts.Gateway):

    def __init__(
        self,
        ingress: str,
        run: restate.context.HandlerType[order_relay.StartRequest, object],
        quote: abc.Callable[[typing.Any, order_relay.QuoteRequest], abc.Awaitable[order_relay.QuoteResponse]],
        ctx: restate.Context | None,
    ) -> None:
        self._ingress = ingress
        self._run = run
        self._quote = quote
        self._ctx = ctx

    async def start(self, request: order_relay.StartRequest) -> order_relay.StartResponse:
        keyed = str(request.order.identity)
        try:
            async with httpx.AsyncClient(base_url=self._ingress) as http:
                await restate.client.Client(http).workflow_send(self._run, key=keyed, arg=request)
        except (restate.HttpError, httpx.TransportError) as e:
            raise errors.InfraError(f"restate ingress refused the workflow: {e}") from e
        return order_relay.StartResponse(order_id=keyed)

    async def quote(self, request: order_relay.QuoteRequest) -> order_relay.QuoteResponse:
        if self._ctx is None:
            raise errors.InfraError("a quote is journaled, so it runs only inside an invocation")
        try:
            return await self._ctx.service_call(self._quote, request)
        except restate.TerminalError as e:
            raise errors.DomainError(errors.Kind.NOT_FOUND, "action_rejected", e.message) from e


class RestateActionJobs(ts.Job):

    def __init__(self, actions: order_actions_client.Client) -> None:
        self.service = restate.Service("OrderingActions")

        @self.service.handler(
            input_serde=RestateQuoteRequestSerde(),
            output_serde=RestateQuoteResponseSerde(),
        )
        async def quote(
            ctx: restate.Context, request: order_relay.QuoteRequest
        ) -> order_relay.QuoteResponse:
            try:
                return actions.quote(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        self.quote = quote

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.service]


class RestateWorkflowJobs(ts.Job):

    def __init__(
        self,
        ingress: str,
        quote: abc.Callable[[typing.Any, order_relay.QuoteRequest], abc.Awaitable[order_relay.QuoteResponse]],
    ) -> None:
        self.workflow = restate.Workflow("Ordering")

        @self.workflow.main(
            input_serde=RestateStartRequestSerde(),
            output_serde=RestateRunResponseSerde(),
        )
        async def run(
            ctx: restate.WorkflowContext, request: order_relay.StartRequest
        ) -> order_orchestrator.RunResponse:
            orchestrator = order_orchestrator.OrderOrchestrator(
                RestateOrderRelay(ingress, run, quote, ctx)
            )
            try:
                return await orchestrator.run(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        self.run = run

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.workflow]
