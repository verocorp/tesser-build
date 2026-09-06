from __future__ import annotations

import collections.abc as abc
import json
import typing

import tesser.adapters as ts
import restate
import restate.serde

import ordering.application.client as client
import ordering.application.orchestrators as orchestrators
import ordering.application.ports as ports
import tesser.errors as errors


class RestateJobContext(ts.JobContext):

    def __init__(self, ctx: restate.Context) -> None:
        self._ctx = ctx

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I  # tesser:debt TB022
    ) -> O:
        return await self._ctx.service_call(step, request)


class RecordSerde[T](ts.Serde, restate.serde.Serde[T]):

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


class RestateActionJobs(ts.Job):

    def __init__(self, ordering_application_client: client.OrderingApplicationClient) -> None:
        self.service = restate.Service("OrderingActions")

        @self.service.handler(
            input_serde=RecordSerde(ports.QuoteRequest),
            output_serde=RecordSerde(ports.QuoteResponse),
        )
        async def quote(ctx: restate.Context, request: ports.QuoteRequest) -> ports.QuoteResponse:  # tesser:debt TB023
            try:
                return ordering_application_client.quote(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        self.quote = quote

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.service]


class RestateWorkflowJobs(ts.Job):

    def __init__(self, quoting: ports.Quoting) -> None:
        self.workflow = restate.Workflow("Ordering")

        @self.workflow.main(
            input_serde=RecordSerde(ports.StartRequest),
            output_serde=RecordSerde(orchestrators.RunResponse),
        )
        async def run(  # tesser:debt TB023
            ctx: restate.WorkflowContext, request: ports.StartRequest
        ) -> orchestrators.RunResponse:
            order_orchestrator = orchestrators.OrderOrchestrator(RestateJobContext(ctx), quoting)
            try:
                return await order_orchestrator.run(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        self.run = run

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.workflow]
