from __future__ import annotations

import tesser.adapters as ts
import restate

import ordering.adapters.gateways.restate_actions as restate_actions
import ordering.adapters.gateways.restate_workflow as restate_workflow
import ordering.application.client.order_actions as order_actions_client
import ordering.application.orchestrators.order_orchestrator as order_orchestrator
import ordering.application.ports.order_actions as order_actions
import ordering.application.ports.order_workflow as order_workflow
import tesser.errors as errors


class RestateJobs(ts.Job):

    def __init__(self, actions: order_actions_client.Client) -> None:
        self.workflow = restate.Workflow("Ordering")
        self.service = restate.Service("OrderingActions")

        @self.service.handler(
            input_serde=restate_workflow.RecordSerde(order_actions.QuoteRequest),
            output_serde=restate_workflow.RecordSerde(order_actions.QuoteResponse),
        )
        async def quote(
            ctx: restate.Context, request: order_actions.QuoteRequest
        ) -> order_actions.QuoteResponse:
            try:
                return actions.quote(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        @self.workflow.main(
            input_serde=restate_workflow.RecordSerde(order_workflow.StartRequest),
            output_serde=restate_workflow.RecordSerde(order_orchestrator.RunResponse),
        )
        async def run(
            ctx: restate.WorkflowContext, request: order_workflow.StartRequest
        ) -> order_orchestrator.RunResponse:
            orchestrator = order_orchestrator.OrderOrchestrator(
                restate_actions.RestateOrderActions(ctx, quote)
            )
            try:
                return await orchestrator.run(request)
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e

        self.run = run
        self.quote = quote

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.workflow, self.service]
