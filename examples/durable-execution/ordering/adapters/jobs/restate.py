from __future__ import annotations

import tesser.adapters as ts
import httpx
import restate
import restate.client
import restate.serde

import ordering.application.client.order_actions as order_actions_client
import ordering.application.orchestrators.order_orchestrator as order_orchestrator
import ordering.application.relays.order_job_context as order_job_context
import ordering.application.relays.order_relay as order_relay
import tesser.errors as errors


class RestateStartRequestSerde(ts.Serde, restate.serde.Serde[order_relay.StartRequest]):

    def serialize(self, obj: order_relay.StartRequest | None) -> bytes:
        if obj is None:
            return b""
        return order_relay.StartRequestSnapshot().serialize(obj)

    def deserialize(self, buf: bytes) -> order_relay.StartRequest | None:
        if not buf:
            return None
        return order_relay.StartRequestSnapshot().deserialize(buf)


class RestateRunResponseSerde(ts.Serde, restate.serde.Serde[order_relay.RunResponse]):

    def serialize(self, obj: order_relay.RunResponse | None) -> bytes:
        if obj is None:
            return b""
        return order_relay.RunResponseSnapshot().serialize(obj)

    def deserialize(self, buf: bytes) -> order_relay.RunResponse | None:
        if not buf:
            return None
        return order_relay.RunResponseSnapshot().deserialize(buf)


class RestateQuoteRequestSerde(ts.Serde, restate.serde.Serde[order_job_context.QuoteRequest]):

    def serialize(self, obj: order_job_context.QuoteRequest | None) -> bytes:
        if obj is None:
            return b""
        return order_job_context.QuoteRequestSnapshot().serialize(obj)

    def deserialize(self, buf: bytes) -> order_job_context.QuoteRequest | None:
        if not buf:
            return None
        return order_job_context.QuoteRequestSnapshot().deserialize(buf)


class RestateQuoteResponseSerde(ts.Serde, restate.serde.Serde[order_job_context.QuoteResponse]):

    def serialize(self, obj: order_job_context.QuoteResponse | None) -> bytes:
        if obj is None:
            return b""
        return order_job_context.QuoteResponseSnapshot().serialize(obj)

    def deserialize(self, buf: bytes) -> order_job_context.QuoteResponse | None:
        if not buf:
            return None
        return order_job_context.QuoteResponseSnapshot().deserialize(buf)


class RestateActionJobs(ts.Job):

    def __init__(self, actions: order_actions_client.Client) -> None:
        self.service = restate.Service("OrderingActions")

        @self.service.handler(
            input_serde=RestateQuoteRequestSerde(),
            output_serde=RestateQuoteResponseSerde(),
        )
        async def quote(
            ctx: restate.Context, request: order_job_context.QuoteRequest
        ) -> order_job_context.QuoteResponse:
            try:
                return actions.quote(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        self.quote = quote

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.service]


class RestateOrderJobContext(ts.JobContext):

    def __init__(self, ctx: restate.Context, actions: RestateActionJobs) -> None:
        self._ctx = ctx
        self._actions = actions

    async def quote(
        self, request: order_job_context.QuoteRequest
    ) -> order_job_context.QuoteResponse:
        try:
            return await self._ctx.service_call(self._actions.quote, request)
        except restate.TerminalError as e:
            raise errors.DomainError(errors.Kind.NOT_FOUND, "action_rejected", e.message) from e


class RestateWorkflowJobs(ts.Job):

    def __init__(self, actions: RestateActionJobs) -> None:
        self.workflow = restate.Workflow("Ordering")

        @self.workflow.main(
            input_serde=RestateStartRequestSerde(),
            output_serde=RestateRunResponseSerde(),
        )
        async def run(
            ctx: restate.WorkflowContext, request: order_relay.StartRequest
        ) -> order_relay.RunResponse:
            orchestrator = order_orchestrator.OrderOrchestrator(
                RestateOrderJobContext(ctx, actions)
            )
            try:
                return await orchestrator.run(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        self.run = run

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.workflow]


class RestateOrderRelay(ts.Gateway):

    def __init__(self, ingress: str, workflows: RestateWorkflowJobs) -> None:
        self._ingress = ingress
        self._workflows = workflows

    async def start(self, request: order_relay.StartRequest) -> order_relay.StartResponse:
        keyed = str(request.order.identity)
        try:
            async with httpx.AsyncClient(base_url=self._ingress) as http:
                await restate.client.Client(http).workflow_send(
                    self._workflows.run, key=keyed, arg=request
                )
        except (restate.HttpError, httpx.TransportError) as e:
            raise errors.InfraError(f"restate ingress refused the workflow: {e}") from e
        return order_relay.StartResponse(keyed)
