from __future__ import annotations

import json

import tesser.adapters as ts
import restate
import restate.serde

import ordering.adapters.jobs.restate_context as restate_context
import ordering.application.client.order_actions as order_actions_client
import ordering.application.orchestrators.order_orchestrator as order_orchestrator
import ordering.application.ports.order_workflow as order_workflow
import ordering.application.ports.quoting as quoting
import tesser.errors as errors


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

    def __init__(self, actions: order_actions_client.Client) -> None:
        self.service = restate.Service("OrderingActions")

        @self.service.handler(
            input_serde=RecordSerde(quoting.QuoteRequest),
            output_serde=RecordSerde(quoting.QuoteResponse),
        )
        async def quote(ctx: restate.Context, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
            try:
                return actions.quote(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        self.quote = quote

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.service]


class RestateWorkflowJobs(ts.Job):

    def __init__(self, quotes: quoting.Quoting) -> None:
        self.workflow = restate.Workflow("Ordering")

        @self.workflow.main(
            input_serde=RecordSerde(order_workflow.StartRequest),
            output_serde=RecordSerde(order_orchestrator.RunResponse),
        )
        async def run(
            ctx: restate.WorkflowContext, request: order_workflow.StartRequest
        ) -> order_orchestrator.RunResponse:
            orchestrator = order_orchestrator.OrderOrchestrator(
                restate_context.RestateJobContext(ctx), quotes
            )
            try:
                return await orchestrator.run(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        self.run = run

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.workflow]
