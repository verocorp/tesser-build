from __future__ import annotations

import tesser.adapters as ts
import restate

import ordering.adapters.gateways.restate_actions as restate_actions
import ordering.adapters.gateways.restate_workflow as restate_workflow
import ordering.application.order_orchestrator as order_orchestrator  # tesser:debt TB060
import ordering.client.client as client
import tesser.errors as errors


class RestateHandlers(ts.Handler):

    def __init__(self, actions: client.Actions) -> None:
        self.workflow = restate.Workflow("Ordering")
        self.service = restate.Service("OrderingActions")

        @self.service.handler(
            input_serde=restate_workflow.RecordSerde(restate_actions.QuoteRequest),
            output_serde=restate_workflow.RecordSerde(restate_actions.QuoteResponse),
        )
        async def quote(
            ctx: restate.Context, request: restate_actions.QuoteRequest
        ) -> restate_actions.QuoteResponse:
            try:
                quoted = actions.quote(client.QuoteRequest(sku=request.sku))
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e
            return restate_actions.QuoteResponse(cents=quoted.cents)

        @self.workflow.main(
            input_serde=restate_workflow.RecordSerde(restate_workflow.RunRequest),
            output_serde=restate_workflow.RecordSerde(restate_workflow.RunResponse),
        )
        async def run(
            ctx: restate.WorkflowContext, request: restate_workflow.RunRequest
        ) -> restate_workflow.RunResponse:
            orchestrator = order_orchestrator.OrderOrchestrator(
                restate_actions.RestateOrderActions(ctx, quote)
            )
            try:
                ran = await orchestrator.run(
                    client.RunRequest(
                        order_id=ctx.key(), sku=request.sku, quantity=request.quantity
                    )
                )
            except errors.DomainError as e:
                raise restate.TerminalError(e.message, status_code=errors.status_for(e.kind)) from e
            return restate_workflow.RunResponse(order_id=ran.order_id, total_cents=ran.total_cents)

        self.run = run
        self.quote = quote

    def definitions(self) -> list[restate.Workflow | restate.Service]:
        return [self.workflow, self.service]
